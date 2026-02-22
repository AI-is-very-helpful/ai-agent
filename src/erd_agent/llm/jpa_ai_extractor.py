from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Tuple

from erd_agent.config import settings
from erd_agent.model import Schema, Table, Column, Ref, EnumType
from erd_agent.llm.aoai_client import build_aoai_client
from erd_agent.llm.schema_models import ExtractedSchema

SYSTEM_PROMPT = """You are a senior backend engineer and data modeler.
You extract relational database schema from Java JPA entity source code.
Focus only on DB schema: tables, columns, primary keys, foreign keys, join tables, and enums.
Return ONLY valid JSON (no markdown, no explanation).

EmbeddedId rule:
If an entity uses @EmbeddedId, DO NOT create a single column for the embedded field (e.g., "id").
Instead, find the corresponding @Embeddable class and EXPAND its fields into individual table columns.
Mark all expanded columns as pk=true and nullable=false.
"""

USER_PROMPT_TEMPLATE = """Analyze the following Java source files and extract database schema.

Rules:
- Tables: classes annotated with @Entity are tables.
- Table name: use @Table(name, schema) if present, else snake_case of @Entity(name) or class name.
- Columns:
  - @Id => pk=true and nullable=false
  - @GeneratedValue => increment=true
  - @Column(name, nullable, unique, length) => map accordingly, length for varchar(length)
  - @Enumerated(EnumType.STRING) => store as enum type if enum definition is available; otherwise varchar.
- Relationships:
  - @ManyToOne / @OneToOne with @JoinColumn(name) => create FK column and Ref.
  - @ManyToMany with @JoinTable => create join table with two FK columns and two Refs.
- Enums:
  - If a field uses an enum (e.g., Role), and the enum definition is provided, create an enum in output.
  - Prefer enum output when @Enumerated(EnumType.STRING) is used.
- EmbeddedId handling:
  - @EmbeddedId indicates a composite primary key.
  - Expand the @Embeddable key class fields into columns.
  - Each expanded column must have pk=true and nullable=false.
  - Do not output the embedded object itself as a column.


Output JSON schema:
{{
  "tables": [
    {{
      "name": "...",
      "columns": [
        {{
          "name": "...",
          "type": "...",
          "pk": false,
          "nullable": true,
          "unique": false,
          "increment": false,
          "default": null,
          "note": null
        }}
      ],
      "note": null
    }}
  ],
  "refs": [
    {{
      "from_table": "...",
      "from_column": "...",
      "to_table": "...",
      "to_column": "...",
      "rel": ">"
    }}
  ],
  "enums": [
    {{
      "name": "...",
      "values": ["..."],
      "note": null
    }}
  ]
}}

FILES:
{files_blob}
"""

def _chunk_files(files: List[Tuple[Path, str]], max_chars: int = 120_000) -> List[List[Tuple[Path, str]]]:
    chunks = []
    cur = []
    cur_len = 0
    for p, txt in files:
        block_len = len(txt)
        if cur and cur_len + block_len > max_chars:
            chunks.append(cur)
            cur = []
            cur_len = 0
        cur.append((p, txt))
        cur_len += block_len
    if cur:
        chunks.append(cur)
    return chunks

def _make_files_blob(chunk: List[Tuple[Path, str]]) -> str:
    parts = []
    for p, txt in chunk:
        parts.append(f'<file path="{p.as_posix()}">\n{txt}\n</file>')
    return "\n\n".join(parts)

def _call_llm(files_blob: str) -> ExtractedSchema:
    client = build_aoai_client()
    if client is None:
        raise RuntimeError("Azure OpenAI 설정이 없습니다. (.env의 AZURE_OPENAI_* 값을 설정하세요)")

    user_prompt = USER_PROMPT_TEMPLATE.format(files_blob=files_blob)

    # gpt-4.1 / api-version 2024-06-01: response_format json_object를 사용해 JSON 안정화
    # (Structured Outputs json_schema는 환경/모델 지원 편차가 있어 우선 json_object로 안전하게) [5](https://github.com/holistics/dbml/blob/master/dbml-homepage/docs/docs.md)[3](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/chatgpt?view=foundry-classic)
    resp = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = resp.choices[0].message.content
    data = json.loads(content)
    return ExtractedSchema.model_validate(data)

def _merge_extracted(chunks: List[ExtractedSchema]) -> ExtractedSchema:
    # 간단 병합: table/enum/ref 이름 기반 union
    tables: Dict[str, Dict[str, object]] = {}
    enums: Dict[str, Dict[str, object]] = {}
    refs_set = set()

    for c in chunks:
        for e in c.enums:
            em = enums.setdefault(e.name, {"name": e.name, "values": set(), "note": e.note})
            em["values"].update(e.values)
            if not em.get("note") and e.note:
                em["note"] = e.note

        for t in c.tables:
            tm = tables.setdefault(t.name, {"name": t.name, "columns": {}, "note": t.note})
            if not tm.get("note") and t.note:
                tm["note"] = t.note
            for col in t.columns:
                cm = tm["columns"].setdefault(col.name, col.model_dump())
                # 충돌 시 보수적으로 병합: pk/unique/increment는 OR, nullable은 AND(더 엄격)
                cm["pk"] = cm.get("pk", False) or col.pk
                cm["unique"] = cm.get("unique", False) or col.unique
                cm["increment"] = cm.get("increment", False) or col.increment
                cm["nullable"] = cm.get("nullable", True) and col.nullable
                # type은 더 구체적인 쪽 우선(varchar -> varchar(255), enum 등)
                if cm.get("type") in ("varchar", "text") and col.type not in ("varchar", "text"):
                    cm["type"] = col.type
                if cm.get("type", "").startswith("varchar") and col.type.startswith("varchar("):
                    cm["type"] = col.type
                if not cm.get("note") and col.note:
                    cm["note"] = col.note

        for r in c.refs:
            key = (r.from_table, r.from_column, r.rel, r.to_table, r.to_column)
            refs_set.add(key)

    merged = {
        "tables": [],
        "refs": [],
        "enums": [],
    }

    for ename, e in enums.items():
        merged["enums"].append({"name": ename, "values": sorted(list(e["values"])), "note": e.get("note")})

    for tname, t in tables.items():
        cols = [t["columns"][k] for k in sorted(t["columns"].keys())]
        merged["tables"].append({"name": tname, "columns": cols, "note": t.get("note")})

    for (ft, fc, rel, tt, tc) in sorted(refs_set):
        merged["refs"].append({"from_table": ft, "from_column": fc, "rel": rel, "to_table": tt, "to_column": tc})

    return ExtractedSchema.model_validate(merged)

def extracted_to_schema(ex: ExtractedSchema) -> Schema:
    schema = Schema()

    for e in ex.enums:
        enum = schema.ensure_enum(e.name)
        enum.values = e.values
        enum.note = e.note

    for t in ex.tables:
        table = schema.ensure_table(t.name)
        table.note = t.note
        for c in t.columns:
            table.columns[c.name] = Column(
                name=c.name,
                db_type=c.type,
                pk=c.pk,
                nullable=c.nullable,
                unique=c.unique,
                increment=c.increment,
                default=c.default,
                note=c.note
            )

    for r in ex.refs:
        schema.refs.append(Ref(
            child_table=r.from_table,
            child_column=r.from_column,
            parent_table=r.to_table,
            parent_column=r.to_column,
            rel=r.rel
        ))
    return schema

def ai_extract_schema(file_texts: List[Tuple[Path, str]]) -> Schema:
    chunks = _chunk_files(file_texts)
    extracted_chunks = []
    for ch in chunks:
        blob = _make_files_blob(ch)
        extracted_chunks.append(_call_llm(blob))
    merged = _merge_extracted(extracted_chunks)
    return extracted_to_schema(merged)
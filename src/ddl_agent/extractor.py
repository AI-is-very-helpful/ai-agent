"""LLM 기반 DDL 추출기."""
from __future__ import annotations
import json
from pathlib import Path

from erd_agent.config import settings
from erd_agent.llm.aoai_client import build_aoai_client
from ddl_agent.models import ExtractedDDL

SYSTEM_PROMPT = """You are a senior DBA and data modeler.
You generate DDL (CREATE TABLE) SQL from Java JPA entity source code.
Focus on producing correct, production-ready DDL.
Return ONLY valid JSON (no markdown, no explanation).
"""

USER_PROMPT_TEMPLATE = """Analyze the following Java JPA entity source files and generate DDL.

Rules:
- @Entity class → CREATE TABLE
- @Table(name, schema) → use the specified table name and schema
- @Id → PRIMARY KEY
- @GeneratedValue → AUTO_INCREMENT (MySQL) or SERIAL (PostgreSQL)
- @Column(name, nullable, unique, length, columnDefinition) → map to DDL column
- @Enumerated(EnumType.STRING) → VARCHAR with CHECK constraint or ENUM type
- @ManyToOne + @JoinColumn → FOREIGN KEY constraint
- @ManyToMany + @JoinTable → generate the join table with two FKs
- @EmbeddedId → expand @Embeddable fields as composite PK columns
- Use appropriate SQL types: String→VARCHAR, Long→BIGINT, Integer→INT, Boolean→TINYINT(1), LocalDateTime→TIMESTAMP, etc.
- Include COMMENT ON TABLE / column if @Table or field has documentation

Detect the likely dialect from imports/config (default MySQL).

Output JSON schema:
{{
  "dialect": "mysql",
  "tables": [
    {{
      "name": "users",
      "schema_name": null,
      "columns": [
        {{
          "name": "id",
          "type": "BIGINT",
          "pk": true,
          "nullable": false,
          "unique": false,
          "auto_increment": true,
          "default": null,
          "comment": "User primary key"
        }}
      ],
      "constraints": [
        {{
          "name": "pk_users",
          "type": "PRIMARY KEY",
          "columns": ["id"],
          "ref_table": null,
          "ref_columns": []
        }},
        {{
          "name": "fk_users_role",
          "type": "FOREIGN KEY",
          "columns": ["role_id"],
          "ref_table": "roles",
          "ref_columns": ["id"]
        }}
      ],
      "comment": "User table"
    }}
  ]
}}

FILES:
{files_blob}
"""


def _chunk_files(files: list[tuple[Path, str]], max_chars: int = 120_000) -> list[list[tuple[Path, str]]]:
    chunks: list[list[tuple[Path, str]]] = []
    cur: list[tuple[Path, str]] = []
    cur_len = 0
    for p, txt in files:
        if cur and cur_len + len(txt) > max_chars:
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append((p, txt))
        cur_len += len(txt)
    if cur:
        chunks.append(cur)
    return chunks


def _make_files_blob(chunk: list[tuple[Path, str]]) -> str:
    parts = []
    for p, txt in chunk:
        parts.append(f'<file path="{p.as_posix()}">\n{txt}\n</file>')
    return "\n\n".join(parts)


def _call_llm(files_blob: str) -> ExtractedDDL:
    client = build_aoai_client()
    if client is None:
        raise RuntimeError("Azure OpenAI 설정이 없습니다.")

    resp = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(files_blob=files_blob)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)
    return ExtractedDDL.model_validate(data)


def _merge_ddls(chunks: list[ExtractedDDL]) -> ExtractedDDL:
    tables: dict[str, dict] = {}
    dialect = "mysql"
    for ddl in chunks:
        dialect = ddl.dialect
        for t in ddl.tables:
            if t.name not in tables:
                tables[t.name] = t.model_dump()
    return ExtractedDDL.model_validate({"dialect": dialect, "tables": list(tables.values())})


def ai_extract_ddl(file_texts: list[tuple[Path, str]]) -> ExtractedDDL:
    chunks = _chunk_files(file_texts)
    extracted = [_call_llm(_make_files_blob(ch)) for ch in chunks]
    return _merge_ddls(extracted)

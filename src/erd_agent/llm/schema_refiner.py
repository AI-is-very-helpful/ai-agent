from __future__ import annotations
import json
from typing import Any
from erd_agent.model import Schema
from erd_agent.config import settings
from erd_agent.llm.aoai_client import build_aoai_client

REFINE_SCHEMA = {
  "type": "object",
  "properties": {
    "tables": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "columns": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "name": {"type": "string"},
                "db_type": {"type": "string"},
                "pk": {"type": "boolean"},
                "nullable": {"type": "boolean"},
                "unique": {"type": "boolean"},
              },
              "required": ["name", "db_type", "pk", "nullable", "unique"],
              "additionalProperties": False
            }
          }
        },
        "required": ["name", "columns"],
        "additionalProperties": False
      }
    },
    "refs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "child_table": {"type": "string"},
          "child_column": {"type": "string"},
          "parent_table": {"type": "string"},
          "parent_column": {"type": "string"},
          "rel": {"type": "string"}
        },
        "required": ["child_table","child_column","parent_table","parent_column","rel"],
        "additionalProperties": False
      }
    }
  },
  "required": ["tables", "refs"],
  "additionalProperties": False
}

def schema_to_min_json(schema: Schema) -> dict[str, Any]:
    return {
        "tables": [
            {
                "name": t.name,
                "columns": [
                    {
                        "name": c.name,
                        "db_type": c.db_type,
                        "pk": c.pk,
                        "nullable": c.nullable,
                        "unique": c.unique,
                    }
                    for c in t.columns.values()
                ],
            }
            for t in schema.tables.values()
        ],
        "refs": [
            {
                "child_table": r.child_table,
                "child_column": r.child_column,
                "parent_table": r.parent_table,
                "parent_column": r.parent_column,
                "rel": r.rel,
            }
            for r in schema.refs
        ],
    }

def apply_refined(schema: Schema, refined: dict[str, Any]) -> None:
    # 간단히 테이블/컬럼/refs를 덮어쓰기(필요 시 merge 전략으로 확장)
    schema.tables.clear()
    schema.refs.clear()
    for t in refined["tables"]:
        table = schema.ensure_table(t["name"])
        for c in t["columns"]:
            table.columns[c["name"]] = __import__("erd_agent.model", fromlist=["Column"]).Column(
                name=c["name"],
                db_type=c["db_type"],
                pk=c["pk"],
                nullable=c["nullable"],
                unique=c["unique"],
            )
    for r in refined["refs"]:
        schema.refs.append(__import__("erd_agent.model", fromlist=["Ref"]).Ref(**r))

def refine_schema_with_aoai(schema: Schema, hints_text: str = "") -> Schema:
    client = build_aoai_client()
    if client is None:
        return schema

    payload = schema_to_min_json(schema)
    system = (
        "You are a senior data modeler. "
        "Refine the extracted relational schema for correctness. "
        "Only adjust when there is strong evidence. Keep names stable."
    )
    user = (
        "Here is a schema extracted from source code. "
        "Return a refined schema in the required JSON format.\n\n"
        f"HINTS:\n{hints_text}\n\n"
        f"SCHEMA:\n{json.dumps(payload, ensure_ascii=False)}"
    )

    # 1) Structured Outputs 시도 (환경에 따라 미지원일 수 있어 try)
    try:
        resp = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "refined_schema", "schema": REFINE_SCHEMA, "strict": True}
            },
        )
        content = resp.choices[0].message.content
        refined = json.loads(content)
        apply_refined(schema, refined)
        return schema
    except Exception:
        # 2) fallback: json_object
        try:
            resp = client.chat.completions.create(
                model=settings.azure_openai_deployment,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                response_format={"type": "json_object"},
            )
            refined = json.loads(resp.choices[0].message.content)
            apply_refined(schema, refined)
        except Exception:
            pass

    return schema
from __future__ import annotations
from erd_agent.model import Schema, Column

def normalize_schema(schema: Schema) -> None:
    # 1) Ref에 등장하는 테이블이 없으면 placeholder 생성
    for r in schema.refs:
        if r.parent_table not in schema.tables:
            t = schema.ensure_table(r.parent_table)
            if "id" not in t.columns:
                t.columns["id"] = Column("id", "bigint", pk=True, nullable=False)
        if r.child_table not in schema.tables:
            t = schema.ensure_table(r.child_table)
            if "id" not in t.columns:
                t.columns["id"] = Column("id", "bigint", pk=True, nullable=False)

    # 2) 모든 테이블에 PK가 없으면 id를 추가(안전장치)
    for t in schema.tables.values():
        if not any(c.pk for c in t.columns.values()):
            if "id" not in t.columns:
                t.columns["id"] = Column("id", "bigint", pk=True, nullable=False)
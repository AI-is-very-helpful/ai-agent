from __future__ import annotations
from pathlib import Path
from erd_agent.model import Schema, Column

def col_settings(c: Column) -> str:
    settings = []
    if c.pk:
        settings.append("pk")
    if c.increment:
        settings.append("increment")
    if c.unique:
        settings.append("unique")
    if not c.nullable:
        settings.append("not null")
    if c.default is not None:
        settings.append(f"default: {c.default}")
    if c.note:
        settings.append(f"note: '{c.note}'")
    return f" [{', '.join(settings)}]" if settings else ""

def to_dbml(schema: Schema) -> str:
    lines: list[str] = []

    # ✅ Enums 먼저 출력
    for ename, enum in sorted(schema.enums.items()):
        lines.append(f"Enum {ename} {{")
        for v in enum.values:
            # 값에 공백/특수문자 있으면 따옴표 필요할 수 있음(간단히 안전 처리)
            safe = f"\"{v}\"" if any(ch.isspace() for ch in v) else v
            lines.append(f"  {safe}")
        if enum.note:
            lines.append(f"  Note: '{enum.note}'")
        lines.append("}\n")

    # Tables
    for tname, table in sorted(schema.tables.items()):
        lines.append(f"Table {tname} {{")
        for _, col in sorted(table.columns.items(), key=lambda kv: (not kv[1].pk, kv[0])):
            lines.append(f"  {col.name} {col.db_type}{col_settings(col)}")
        if table.note:
            lines.append(f"  Note: '{table.note}'")
        lines.append("}\n")

    # Refs
    for r in schema.refs:
        lines.append(f"Ref: {r.child_table}.{r.child_column} {r.rel} {r.parent_table}.{r.parent_column}")

    lines.append("")
    return "\n".join(lines)

def write_dbml(schema: Schema, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(to_dbml(schema), encoding="utf-8")
    return out_path
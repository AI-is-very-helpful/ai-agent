from __future__ import annotations
from pathlib import Path
from erd_agent.model import Schema

def write_summary_md(schema: Schema, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# ERD Summary\n")
    lines.append(f"- Tables: {len(schema.tables)}")
    lines.append(f"- Relationships(Refs): {len(schema.refs)}\n")

    lines.append("## Tables\n")
    for tname, table in sorted(schema.tables.items()):
        lines.append(f"### {tname}")
        for col in table.columns.values():
            flags = []
            if col.pk: flags.append("PK")
            if col.increment: flags.append("AI")
            if col.unique: flags.append("UNIQUE")
            if not col.nullable: flags.append("NOT NULL")
            flag_s = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"- `{col.name}`: {col.db_type}{flag_s}")
        lines.append("")

    lines.append("## Relationships\n")
    for r in schema.refs:
        lines.append(f"- {r.child_table}.{r.child_column} {r.rel} {r.parent_table}.{r.parent_column}")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
``
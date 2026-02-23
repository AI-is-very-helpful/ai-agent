"""DDL 문서 생성: JPA Entity 스캔 → LLM 분석 → SQL 출력."""
from __future__ import annotations
from pathlib import Path

from rich.console import Console

from erd_agent.config import settings
from erd_agent.repo import prepare_repo
from erd_agent.scanner import (
    scan_repo,
    find_enum_type_names_in_entity_text,
    find_enum_definition_files,
    find_embedded_id_type_names_in_entity_text,
    find_embeddable_definition_files,
)
from ddl_agent.extractor import ai_extract_ddl
from ddl_agent.writer import write_ddl

console = Console()


def _load(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def run_ddl(
    repo: str,
    out_dir: Path | None = None,
    out_file: str = "schema.sql",
) -> Path:
    repo_path = prepare_repo(repo)
    base = out_dir or settings.doc_output_dir / "ddl"
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / out_file

    console.print(f"[bold]Repo:[/bold] {repo_path}")

    entity_files = scan_repo(repo_path)
    console.print(f"Found [green]{len(entity_files)}[/green] JPA entity candidates")

    if not entity_files:
        out_path.write_text("-- No JPA entities found.\n", encoding="utf-8")
        console.print(f"[bold green]DDL:[/bold green] {out_path}")
        return out_path

    entity_texts = [(f.relative_to(repo_path), _load(f)) for f in entity_files]

    enum_names: set[str] = set()
    embedded_id_names: set[str] = set()
    for _, txt in entity_texts:
        enum_names |= find_enum_type_names_in_entity_text(txt)
        embedded_id_names |= find_embedded_id_type_names_in_entity_text(txt)

    enum_files = find_enum_definition_files(repo_path, enum_names)
    embeddable_files = find_embeddable_definition_files(repo_path, embedded_id_names)
    enum_texts = [(f.relative_to(repo_path), _load(f)) for f in enum_files]
    embeddable_texts = [(f.relative_to(repo_path), _load(f)) for f in embeddable_files]

    all_inputs = [(repo_path / p, txt) for p, txt in entity_texts + enum_texts + embeddable_texts]

    ddl = ai_extract_ddl(all_inputs)
    write_ddl(ddl, out_path)
    console.print(f"[bold green]DDL:[/bold green] {out_path}")
    return out_path

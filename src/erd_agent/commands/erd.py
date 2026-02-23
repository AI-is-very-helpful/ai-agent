"""ERD 문서 생성: JPA Entity → DBML + 요약 MD."""
from __future__ import annotations
from pathlib import Path

from rich.console import Console

from erd_agent.config import settings
from erd_agent.repo import prepare_repo
from erd_agent.model import Schema
from erd_agent.normalize import normalize_schema
from erd_agent.dbml_writer import write_dbml
from erd_agent.docs_writer import write_summary_md
from erd_agent.llm.schema_refiner import refine_schema_with_aoai
from erd_agent.llm.jpa_ai_extractor import ai_extract_schema
from erd_agent.scanner import (
    scan_repo,
    find_enum_type_names_in_entity_text,
    find_enum_definition_files,
    find_embedded_id_type_names_in_entity_text,
    find_embeddable_definition_files,
)

console = Console()


def load_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def run_erd(
    repo: str,
    out_dir: Path | None = None,
    out_dbml: str = "database.dbml",
    out_md: str = "erd_summary.md",
    use_aoai: bool = False,
    ai_first: bool = False,
) -> tuple[Path, Path]:
    """
    저장소를 분석해 ERD(DBML + 요약 MD)를 생성한다.
    반환: (dbml_path, md_path)
    """
    repo_path = prepare_repo(repo)
    base = out_dir or settings.doc_output_dir / "erd"
    base.mkdir(parents=True, exist_ok=True)
    dbml_path = base / out_dbml
    md_path = base / out_md

    console.print(f"[bold]Repo:[/bold] {repo_path}")
    entity_files = scan_repo(repo_path)
    console.print(f"Found [green]{len(entity_files)}[/green] JPA entity candidates")

    if ai_first:
        console.print("[yellow]AI-first mode: using Azure OpenAI for full analysis[/yellow]")
        entity_texts = [(f.relative_to(repo_path), load_text(f)) for f in entity_files]
        enum_names = set()
        embedded_id_names = set()
        for _, txt in entity_texts:
            enum_names |= find_enum_type_names_in_entity_text(txt)
            embedded_id_names |= find_embedded_id_type_names_in_entity_text(txt)
        enum_files = find_enum_definition_files(repo_path, enum_names)
        embeddable_files = find_embeddable_definition_files(repo_path, embedded_id_names)
        enum_texts = [(f.relative_to(repo_path), load_text(f)) for f in enum_files]
        embeddable_texts = [(f.relative_to(repo_path), load_text(f)) for f in embeddable_files]
        all_inputs = entity_texts + enum_texts + embeddable_texts
        console.print(
            f"AI input files: entities={len(entity_texts)}, enums={len(enum_texts)}, embeddables={len(embeddable_texts)}"
        )
        schema = ai_extract_schema([(repo_path / p, txt) for p, txt in all_inputs])
    else:
        schema = Schema()
        from erd_agent.parsers.jpa_java import JPAJavaParser
        parsers = [JPAJavaParser()]
        for f in entity_files:
            text = load_text(f)
            for p in parsers:
                if p.can_parse(f, text):
                    p.parse(f, text, schema)
        if use_aoai:
            console.print("[yellow]Refining schema with Azure OpenAI (optional)[/yellow]")
            schema = refine_schema_with_aoai(schema)

    normalize_schema(schema)
    write_dbml(schema, dbml_path)
    write_summary_md(schema, md_path)
    console.print(f"[bold green]DBML:[/bold green] {dbml_path}")
    console.print(f"[bold green]MD:[/bold green]   {md_path}")
    return dbml_path, md_path

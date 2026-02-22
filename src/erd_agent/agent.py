from __future__ import annotations
from pathlib import Path
import typer
from rich.console import Console

from erd_agent.config import settings
from erd_agent.repo import prepare_repo
from erd_agent.model import Schema
from erd_agent.normalize import normalize_schema
from erd_agent.dbml_writer import write_dbml
from erd_agent.docs_writer import write_summary_md

# 기존 보정 옵션(정적 결과 보정)
from erd_agent.llm.schema_refiner import refine_schema_with_aoai

# ✅ AI-first extractor
from erd_agent.llm.jpa_ai_extractor import ai_extract_schema

from erd_agent.scanner import (
    scan_repo,
    find_enum_type_names_in_entity_text,
    find_enum_definition_files,
    find_embedded_id_type_names_in_entity_text,   # ✅ 추가
    find_embeddable_definition_files,             # ✅ 추가
)

app = typer.Typer(add_completion=False)
console = Console()

def load_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

@app.command()
def generate(
    repo: str = typer.Argument(..., help="로컬 경로 또는 https git URL"),
    out_dbml: str = typer.Option("database.dbml", help="출력 DBML 파일명"),
    out_md: str = typer.Option("erd_summary.md", help="출력 요약 MD 파일명"),
    use_aoai: bool = typer.Option(False, help="(정적 모드) Azure OpenAI로 스키마 보정(옵션)"),
    ai_first: bool = typer.Option(False, help="AI-first 모드: 정적 분석을 건너뛰고 Azure OpenAI로 전체 분석"),
):
    repo_path = prepare_repo(repo)
    console.print(f"[bold]Repo:[/bold] {repo_path}")

    # 1) 후보 파일 스캔(공통)
    entity_files = scan_repo(repo_path)
    console.print(f"Found [green]{len(entity_files)}[/green] JPA entity candidates")

    settings.erd_output_dir.mkdir(parents=True, exist_ok=True)
    dbml_path = settings.erd_output_dir / out_dbml
    md_path = settings.erd_output_dir / out_md

    # ✅ 2) AI-first 모드
    if ai_first:
        console.print("[yellow]AI-first mode enabled: using Azure OpenAI for full analysis[/yellow]")

        # Entity 파일 텍스트 준비
        entity_texts = [(f.relative_to(repo_path), load_text(f)) for f in entity_files]

        # @Enumerated(EnumType.STRING) enum 타입 이름 모아서 enum 정의 파일도 추가
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

        normalize_schema(schema)
        write_dbml(schema, dbml_path)
        write_summary_md(schema, md_path)
        console.print(f"[bold green]DBML:[/bold green] {dbml_path}")
        console.print(f"[bold green]MD:[/bold green]   {md_path}")
        return

    # 3) 기존 정적 분석 모드(그대로 유지)
    schema = Schema()
    from erd_agent.parsers.jpa_java import JPAJavaParser
    parsers = [JPAJavaParser()]

    for f in entity_files:
        text = load_text(f)
        for p in parsers:
            if p.can_parse(f, text):
                p.parse(f, text, schema)

    normalize_schema(schema)

    if use_aoai:
        console.print("[yellow]Refining schema with Azure OpenAI (optional)[/yellow]")
        schema = refine_schema_with_aoai(schema)
        normalize_schema(schema)

    write_dbml(schema, dbml_path)
    write_summary_md(schema, md_path)

    console.print(f"[bold green]DBML:[/bold green] {dbml_path}")
    console.print(f"[bold green]MD:[/bold green]   {md_path}")

if __name__ == "__main__":
    app()
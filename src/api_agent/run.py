"""API 스펙 문서 생성: Controller 스캔 → LLM 분석 → Markdown 출력."""
from __future__ import annotations
from pathlib import Path

from rich.console import Console

from erd_agent.config import settings
from erd_agent.repo import prepare_repo
from api_agent.scanner import scan_controller_files
from api_agent.extractor import ai_extract_api
from api_agent.writer import write_api_spec

console = Console()


def _load(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def run_api(
    repo: str,
    out_dir: Path | None = None,
    out_file: str = "api_spec.md",
) -> Path:
    repo_path = prepare_repo(repo)
    base = out_dir or settings.doc_output_dir / "api"
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / out_file

    console.print(f"[bold]Repo:[/bold] {repo_path}")

    controller_files = scan_controller_files(repo_path)
    console.print(f"Found [green]{len(controller_files)}[/green] controller candidates")

    if not controller_files:
        out_path.write_text("# API Specification\n\nNo controllers found.\n", encoding="utf-8")
        console.print(f"[bold green]API spec:[/bold green] {out_path}")
        return out_path

    file_texts = [(f, _load(f)) for f in controller_files]
    spec = ai_extract_api(file_texts)
    write_api_spec(spec, out_path)
    console.print(f"[bold green]API spec:[/bold green] {out_path}")
    return out_path

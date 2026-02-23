"""기술 스택 문서 생성: 빌드 파일 스캔 → LLM 분석 → Markdown 출력."""
from __future__ import annotations
from pathlib import Path

from rich.console import Console

from erd_agent.config import settings
from erd_agent.repo import prepare_repo
from stack_agent.scanner import scan_stack_files
from stack_agent.extractor import ai_extract_stack
from stack_agent.writer import write_stack

console = Console()


def _load(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def run_stack(
    repo: str,
    out_dir: Path | None = None,
    out_file: str = "tech_stack.md",
) -> Path:
    repo_path = prepare_repo(repo)
    base = out_dir or settings.doc_output_dir / "stack"
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / out_file

    console.print(f"[bold]Repo:[/bold] {repo_path}")

    stack_files = scan_stack_files(repo_path)
    console.print(f"Found [green]{len(stack_files)}[/green] build/dependency files")

    if not stack_files:
        out_path.write_text("# Tech Stack\n\nNo build/dependency files found.\n", encoding="utf-8")
        console.print(f"[bold green]Tech stack:[/bold green] {out_path}")
        return out_path

    file_texts = [(f, _load(f)) for f in stack_files]
    stack = ai_extract_stack(file_texts)
    write_stack(stack, out_path)
    console.print(f"[bold green]Tech stack:[/bold green] {out_path}")
    return out_path

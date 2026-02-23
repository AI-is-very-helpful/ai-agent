"""아키텍처 문서 생성: 프로젝트 스캔 → LLM 분석 → Mermaid/Markdown 출력."""
from __future__ import annotations
from pathlib import Path

from rich.console import Console

from erd_agent.config import settings
from erd_agent.repo import prepare_repo
from arch_agent.scanner import scan_arch_files, collect_directory_tree
from arch_agent.extractor import ai_extract_architecture
from arch_agent.writer import write_architecture

console = Console()


def _load(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def run_arch(
    repo: str,
    out_dir: Path | None = None,
    out_file: str = "architecture.md",
) -> Path:
    repo_path = prepare_repo(repo)
    base = out_dir or settings.doc_output_dir / "arch"
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / out_file

    console.print(f"[bold]Repo:[/bold] {repo_path}")

    arch_files = scan_arch_files(repo_path)
    dir_tree = collect_directory_tree(repo_path)
    console.print(f"Found [green]{len(arch_files)}[/green] architecture-relevant files")

    if not arch_files:
        out_path.write_text(
            f"# Architecture\n\nNo architecture-relevant files found in {repo_path}.\n",
            encoding="utf-8",
        )
        console.print(f"[bold green]Architecture:[/bold green] {out_path}")
        return out_path

    file_texts = [(f, _load(f)) for f in arch_files]
    arch = ai_extract_architecture(file_texts, dir_tree)
    write_architecture(arch, out_path)
    console.print(f"[bold green]Architecture:[/bold green] {out_path}")
    return out_path

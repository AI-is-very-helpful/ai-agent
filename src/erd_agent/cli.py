"""
프로젝트 문서화 CLI.
- ai-agent: 옵션 플래그로 선택 (--erd --api 등)
- doc-agent: 통합 (all / erd / api / arch / ddl / stack)
- erd-agent, api-agent, arch-agent, ddl-agent, stack-agent: 개별 실행
"""
from __future__ import annotations
from pathlib import Path

import typer
from rich.console import Console

from erd_agent.config import settings
from erd_agent.commands import erd as cmd_erd
from api_agent import run_api
from arch_agent import run_arch
from ddl_agent import run_ddl
from stack_agent import run_stack

console = Console()

# ----- ai-agent: 플래그로 생성할 문서 선택 (--erd --api ...) -----
ai_agent = typer.Typer(
    name="ai-agent",
    add_completion=False,
    help="옵션으로 생성할 문서 선택. 예: ai-agent ./my-project --erd --api",
)


@ai_agent.callback(invoke_without_command=True)
def ai_main(
    repo: str = typer.Argument(..., help="로컬 경로 또는 Git URL"),
    erd: bool = typer.Option(False, "--erd", "-e", help="ERD 생성 (DBML + 요약 MD)"),
    api: bool = typer.Option(False, "--api", "-a", help="API 스펙 문서 생성"),
    arch: bool = typer.Option(False, "--arch", help="아키텍처 다이어그램 문서 생성"),
    ddl: bool = typer.Option(False, "--ddl", "-d", help="DDL 문서 생성"),
    stack: bool = typer.Option(False, "--stack", "-s", help="기술 스택 문서 생성"),
    use_aoai: bool = typer.Option(False, help="(ERD) 정적 모드 시 Azure OpenAI 스키마 보정"),
    ai_first: bool = typer.Option(False, help="(ERD) AI-first 모드로 전체 분석"),
):
    """지정한 옵션만큼만 문서 생성. 옵션 없으면 전체 생성."""
    base = settings.doc_output_dir
    any_ = erd or api or arch or ddl or stack
    if not any_:
        erd = api = arch = ddl = stack = True
        console.print("[bold]No options given → generating all docs.[/bold]")

    if erd:
        cmd_erd.run_erd(
            repo,
            out_dir=base / "erd",
            use_aoai=use_aoai,
            ai_first=ai_first,
        )
    if api:
        run_api(repo, out_dir=base / "api")
    if arch:
        run_arch(repo, out_dir=base / "arch")
    if ddl:
        run_ddl(repo, out_dir=base / "ddl")
    if stack:
        run_stack(repo, out_dir=base / "stack")

    console.print(f"[bold green]Done. Output under[/bold green] {base}")


# ----- 통합 앱: doc-agent (서브커맨드) -----
app = typer.Typer(
    name="doc-agent",
    add_completion=False,
    help="프로젝트 문서화 도구: API 스펙, 아키텍처, DDL, ERD, 기술 스택 문서 생성",
)


def _repo_arg() -> str:
    return typer.Argument(..., help="로컬 경로 또는 Git URL")


@app.command("erd")
def doc_erd(
    repo: str = _repo_arg(),
    out_dbml: str = typer.Option("database.dbml", help="출력 DBML 파일명"),
    out_md: str = typer.Option("erd_summary.md", help="출력 요약 MD 파일명"),
    use_aoai: bool = typer.Option(False, help="(정적 모드) Azure OpenAI 스키마 보정"),
    ai_first: bool = typer.Option(False, help="AI-first 모드로 전체 분석"),
):
    """ERD 문서만 생성 (DBML + 요약 MD)."""
    out_dir = settings.doc_output_dir / "erd"
    cmd_erd.run_erd(
        repo,
        out_dir=out_dir,
        out_dbml=out_dbml,
        out_md=out_md,
        use_aoai=use_aoai,
        ai_first=ai_first,
    )


@app.command("api")
def doc_api(
    repo: str = _repo_arg(),
    out_file: str = typer.Option("api_spec.md", help="출력 파일명"),
):
    """API 스펙 문서만 생성."""
    out_dir = settings.doc_output_dir / "api"
    run_api(repo, out_dir=out_dir, out_file=out_file)


@app.command("arch")
def doc_arch(
    repo: str = _repo_arg(),
    out_file: str = typer.Option("architecture.md", help="출력 파일명"),
):
    """아키텍처 다이어그램 문서만 생성."""
    out_dir = settings.doc_output_dir / "arch"
    run_arch(repo, out_dir=out_dir, out_file=out_file)


@app.command("ddl")
def doc_ddl(
    repo: str = _repo_arg(),
    out_file: str = typer.Option("schema.sql", help="출력 DDL 파일명"),
):
    """DDL 문서만 생성."""
    out_dir = settings.doc_output_dir / "ddl"
    run_ddl(repo, out_dir=out_dir, out_file=out_file)


@app.command("stack")
def doc_stack(
    repo: str = _repo_arg(),
    out_file: str = typer.Option("tech_stack.md", help="출력 파일명"),
):
    """기술 스택 문서만 생성."""
    out_dir = settings.doc_output_dir / "stack"
    run_stack(repo, out_dir=out_dir, out_file=out_file)


@app.command("all")
def doc_all(
    repo: str = _repo_arg(),
    out_dbml: str = typer.Option("database.dbml", help="ERD DBML 파일명"),
    out_md: str = typer.Option("erd_summary.md", help="ERD 요약 MD 파일명"),
    use_aoai: bool = typer.Option(False, help="ERD 정적 모드 시 Azure OpenAI 보정"),
    ai_first: bool = typer.Option(False, help="ERD AI-first 모드"),
):
    """모든 문서 생성: API 스펙, 아키텍처, DDL, ERD, 기술 스택."""
    console.print("[bold]Generating all docs...[/bold]")
    base = settings.doc_output_dir
    cmd_erd.run_erd(repo, out_dir=base / "erd", out_dbml=out_dbml, out_md=out_md, use_aoai=use_aoai, ai_first=ai_first)
    run_api(repo, out_dir=base / "api")
    run_arch(repo, out_dir=base / "arch")
    run_ddl(repo, out_dir=base / "ddl")
    run_stack(repo, out_dir=base / "stack")
    console.print(f"[bold green]All docs written under[/bold green] {base}")


# ----- 개별 진입점: erd-agent, api-agent, arch-agent, ddl-agent, stack-agent -----

erd_app = typer.Typer(add_completion=False)


@erd_app.callback(invoke_without_command=True)
def erd_main(
    repo: str = typer.Argument(..., help="로컬 경로 또는 Git URL"),
    out_dbml: str = typer.Option("database.dbml", help="출력 DBML 파일명"),
    out_md: str = typer.Option("erd_summary.md", help="출력 요약 MD 파일명"),
    use_aoai: bool = typer.Option(False, help="(정적 모드) Azure OpenAI 스키마 보정"),
    ai_first: bool = typer.Option(False, help="AI-first 모드"),
):
    """ERD만 생성 (erd-agent ./my-project)."""
    out_dir = settings.doc_output_dir / "erd"
    cmd_erd.run_erd(repo, out_dir=out_dir, out_dbml=out_dbml, out_md=out_md, use_aoai=use_aoai, ai_first=ai_first)


api_app = typer.Typer(add_completion=False)


@api_app.callback(invoke_without_command=True)
def api_main(
    repo: str = typer.Argument(..., help="로컬 경로 또는 Git URL"),
    out_file: str = typer.Option("api_spec.md", help="출력 파일명"),
):
    """API 스펙 문서만 생성 (api-agent ./my-project)."""
    run_api(repo, out_file=out_file)


arch_app = typer.Typer(add_completion=False)


@arch_app.callback(invoke_without_command=True)
def arch_main(
    repo: str = typer.Argument(..., help="로컬 경로 또는 Git URL"),
    out_file: str = typer.Option("architecture.md", help="출력 파일명"),
):
    """아키텍처 문서만 생성 (arch-agent ./my-project)."""
    run_arch(repo, out_file=out_file)


ddl_app = typer.Typer(add_completion=False)


@ddl_app.callback(invoke_without_command=True)
def ddl_main(
    repo: str = typer.Argument(..., help="로컬 경로 또는 Git URL"),
    out_file: str = typer.Option("schema.sql", help="출력 DDL 파일명"),
):
    """DDL 문서만 생성 (ddl-agent ./my-project)."""
    run_ddl(repo, out_file=out_file)


stack_app = typer.Typer(add_completion=False)


@stack_app.callback(invoke_without_command=True)
def stack_main(
    repo: str = typer.Argument(..., help="로컬 경로 또는 Git URL"),
    out_file: str = typer.Option("tech_stack.md", help="출력 파일명"),
):
    """기술 스택 문서만 생성 (stack-agent ./my-project)."""
    run_stack(repo, out_file=out_file)

import json
import logging
import sys
import tempfile
from pathlib import Path

import azure.functions as func

app = func.FunctionApp()

# ---------------------------------------------------------------
# 1) Azure Functions 고객 패키지 경로 보장
#    GitHub Actions: pip install --target=".python_packages/lib/site-packages"
# ---------------------------------------------------------------
def _ensure_customer_site_packages_on_syspath() -> None:
    base_dir = Path(__file__).resolve().parent
    candidates = [
        Path("/home/site/wwwroot/.python_packages/lib/site-packages"),
        base_dir / ".python_packages" / "lib" / "site-packages",
    ]
    lib_dir = base_dir / ".python_packages" / "lib"
    if lib_dir.exists():
        candidates += list(lib_dir.glob("python*/site-packages"))

    for p in candidates:
        if p.exists():
            sp = str(p)
            if sp not in sys.path:
                sys.path.insert(0, sp)
            logging.info(f"Customer site-packages enabled: {sp}")
            return

    logging.warning("Customer site-packages path not found. Imports may fail.")


_ensure_customer_site_packages_on_syspath()

# ---------------------------------------------------------------
# 2) 모드별 출력 파일 정의
# ---------------------------------------------------------------
VALID_MODES = {"erd", "api", "arch", "ddl", "stack", "all"}

MODE_TO_OUTPUT_FILES: dict[str, list[tuple[str, str]]] = {
    "erd":   [("erd/database.dbml", "text/plain"), ("erd/erd_summary.md", "text/markdown")],
    "api":   [("api/api_spec.md", "text/markdown")],
    "arch":  [("arch/architecture.md", "text/markdown")],
    "ddl":   [("ddl/schema.sql", "text/plain")],
    "stack": [("stack/tech_stack.md", "text/markdown")],
}


def _all_output_files() -> list[tuple[str, str]]:
    result = []
    for files in MODE_TO_OUTPUT_FILES.values():
        result.extend(files)
    return result


def _read_text_file(file_path: Path, max_chars: int = 250_000) -> str:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n... (truncated)"
    return text


def _error(code: str, message: str, details: str = "", status: int = 500) -> func.HttpResponse:
    payload = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details[:20_000]
    return func.HttpResponse(
        json.dumps(payload, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
    )


# ---------------------------------------------------------------
# 3) 에이전트 직접 호출 (Typer/sys.argv 우회 → out_dir 직접 전달)
# ---------------------------------------------------------------
def _run_agents(repo_url: str, mode: str, out_dir: Path) -> list[str]:
    """선택된 모드의 에이전트를 실행. 실패한 에이전트 이름 목록을 반환."""
    from erd_agent.commands import erd as cmd_erd
    from api_agent import run_api
    from arch_agent import run_arch
    from ddl_agent import run_ddl
    from stack_agent import run_stack

    tasks: dict[str, tuple] = {
        "erd":   (cmd_erd.run_erd, {"repo": repo_url, "out_dir": out_dir / "erd"}),
        "api":   (run_api,         {"repo": repo_url, "out_dir": out_dir / "api"}),
        "arch":  (run_arch,        {"repo": repo_url, "out_dir": out_dir / "arch"}),
        "ddl":   (run_ddl,         {"repo": repo_url, "out_dir": out_dir / "ddl"}),
        "stack": (run_stack,       {"repo": repo_url, "out_dir": out_dir / "stack"}),
    }

    run_modes = list(tasks.keys()) if mode == "all" else [mode]
    failed: list[str] = []

    for m in run_modes:
        fn, kwargs = tasks[m]
        try:
            logging.info(f"Running agent: {m}")
            fn(**kwargs)
            logging.info(f"Agent done: {m}")
        except Exception:
            logging.exception(f"Agent failed: {m}")
            failed.append(m)

    return failed


# ---------------------------------------------------------------
# 4) HTTP 엔드포인트
# ---------------------------------------------------------------
@app.route(route="run", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def run(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("run() called")

    # 요청 파싱
    try:
        body = req.get_json()
        logging.info(f"Request body keys: {list(body.keys()) if isinstance(body, dict) else body}")
    except Exception:
        logging.exception("BAD_JSON")
        return _error("BAD_JSON", "Request body must be valid JSON", status=400)

    repo_url = body.get("repo_url") if isinstance(body, dict) else None
    mode = (body.get("mode") or "all").lower() if isinstance(body, dict) else "all"

    if not repo_url or not isinstance(repo_url, str):
        return _error("MISSING_REPO_URL", "repo_url is required", status=400)

    if mode not in VALID_MODES:
        return _error(
            "INVALID_MODE",
            f"mode must be one of {sorted(VALID_MODES)}",
            status=400,
        )

    # 임시 출력 디렉터리 (Azure Functions 쓰기 가능 경로)
    out_dir = Path(tempfile.mkdtemp(prefix="docagent_"))
    logging.info(f"Output dir: {out_dir}")

    # 에이전트 실행
    try:
        failed_agents = _run_agents(repo_url, mode, out_dir)
    except Exception as e:
        logging.exception("AGENT_FAILED (unexpected)")
        return _error("AGENT_FAILED", "Agent execution failed", details=str(e), status=500)

    # 산출물 수집
    output_file_defs = (
        _all_output_files() if mode == "all" else MODE_TO_OUTPUT_FILES.get(mode, [])
    )

    artifacts: list[dict] = []
    missing: list[str] = []

    for rel_path, content_type in output_file_defs:
        fpath = out_dir / rel_path
        if fpath.exists():
            artifacts.append(
                {
                    "name": fpath.name,
                    "path": rel_path,
                    "content_type": content_type,
                    "content": _read_text_file(fpath),
                }
            )
        else:
            missing.append(rel_path)

    summary = artifacts[0]["content"][:2_000] if artifacts else ""

    resp = {
        "status": "ok" if not failed_agents else "partial",
        "repo_url": repo_url,
        "mode": mode,
        "summary": summary,
        "artifacts": artifacts,
        "warnings": (
            [{"missing_files": missing}] if missing else []
        ) + (
            [{"failed_agents": failed_agents}] if failed_agents else []
        ),
        "logs": {"output_dir": str(out_dir)},
    }

    return func.HttpResponse(
        json.dumps(resp, ensure_ascii=False),
        status_code=200,
        mimetype="application/json",
    )

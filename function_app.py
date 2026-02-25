"""
Azure Function HTTP Trigger — POST /api/run

Copilot Studio → Azure Function → 5개 에이전트 실행 → JSON 응답

요청:  { "repo_url": "https://github.com/org/repo.git", "mode": "all" }
응답:  { "status": "ok", "artifacts": [...], ... }
"""
import json
import logging
import tempfile
from pathlib import Path

import azure.functions as func

from erd_agent.commands.erd import run_erd
from erd_agent.repo import prepare_repo
from api_agent.run import run_api
from arch_agent.run import run_arch
from ddl_agent.run import run_ddl
from stack_agent.run import run_stack

app = func.FunctionApp()

VALID_MODES = {"erd", "api", "arch", "ddl", "stack", "all"}

AGENTS = {
    "erd":   {"fn": run_erd,   "outputs": [("database.dbml", "text/plain"), ("erd_summary.md", "text/markdown")]},
    "api":   {"fn": run_api,   "outputs": [("api_spec.md", "text/markdown")]},
    "arch":  {"fn": run_arch,  "outputs": [("architecture.md", "text/markdown")]},
    "ddl":   {"fn": run_ddl,   "outputs": [("schema.sql", "text/plain")]},
    "stack": {"fn": run_stack, "outputs": [("tech_stack.md", "text/markdown")]},
}


def _json_response(body: dict, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
    )


def _error_response(code: str, message: str, status: int = 400) -> func.HttpResponse:
    return _json_response({"error": {"code": code, "message": message}}, status=status)


def _read_file(path: Path, max_chars: int = 250_000) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:max_chars] + "\n\n... (truncated)" if len(text) > max_chars else text


@app.route(route="run", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def run(req: func.HttpRequest) -> func.HttpResponse:
    # ── 1. 요청 파싱 ──
    try:
        body = req.get_json()
    except Exception:
        return _error_response("BAD_JSON", "요청 본문이 유효한 JSON이 아닙니다.")

    repo_url = body.get("repo_url", "")
    mode = body.get("mode", "all").lower()

    if not repo_url:
        return _error_response("MISSING_REPO_URL", "repo_url은 필수입니다.")
    if mode not in VALID_MODES:
        return _error_response("INVALID_MODE", f"mode는 {sorted(VALID_MODES)} 중 하나여야 합니다.")

    # ── 2. 레포 준비 (clone 또는 로컬 경로) ──
    try:
        repo_path = prepare_repo(repo_url)
    except Exception as e:
        logging.exception("REPO_FAILED")
        return _json_response(
            {"error": {"code": "REPO_FAILED", "message": f"레포 준비 실패: {e}"}},
            status=500,
        )

    # ── 3. 에이전트 실행 ──
    out_dir = Path(tempfile.mkdtemp(prefix="docagent_"))
    modes_to_run = list(AGENTS.keys()) if mode == "all" else [mode]

    results: dict[str, dict] = {}
    for m in modes_to_run:
        agent = AGENTS[m]
        agent_out = out_dir / m
        try:
            agent["fn"](repo=str(repo_path), out_dir=agent_out)
            results[m] = {"status": "ok"}
        except Exception as e:
            logging.exception(f"Agent failed: {m}")
            results[m] = {"status": "error", "message": str(e)[:500]}

    # ── 4. 산출물 수집 ──
    artifacts = []
    for m in modes_to_run:
        if results[m]["status"] != "ok":
            continue
        agent_out = out_dir / m
        for filename, content_type in AGENTS[m]["outputs"]:
            fpath = agent_out / filename
            if fpath.exists():
                artifacts.append({
                    "name": filename,
                    "agent": m,
                    "content_type": content_type,
                    "content": _read_file(fpath),
                })

    # ── 5. 응답 ──
    all_ok = all(r["status"] == "ok" for r in results.values())
    return _json_response({
        "status": "ok" if all_ok else "partial",
        "repo_url": repo_url,
        "mode": mode,
        "summary": artifacts[0]["content"][:2_000] if artifacts else "",
        "agents": results,
        "artifacts": artifacts,
    })

import json
import logging
import os
import sys
import tempfile
from pathlib import Path

import azure.functions as func

app = func.FunctionApp()

# -----------------------------
# 1) Azure Functions에서 고객 패키지 경로(sys.path) 보장
#   - Python worker의 customer packages 경로는 보통:
#     /home/site/wwwroot/.python_packages/lib/site-packages  [1](https://microsoft.github.io/teams-sdk/python/in-depth-guides/)
#   - GitHub Actions에서 .python_packages/lib/site-packages에 설치하는 패턴과 맞춤
# -----------------------------
def _ensure_customer_site_packages_on_syspath():
    candidates = []

    # (A) Azure Functions 런타임에서 일반적으로 쓰는 절대경로
    candidates.append(Path("/home/site/wwwroot/.python_packages/lib/site-packages"))

    # (B) run-from-package/zip 배포 시 wwwroot 기준 상대경로
    base_dir = Path(__file__).resolve().parent
    candidates.append(base_dir / ".python_packages" / "lib" / "site-packages")

    # (C) 혹시 python 버전이 폴더명에 포함되는 형태로 들어간 경우 대비(드물지만 방어)
    #     .python_packages/lib/python3.12/site-packages 같은 형태
    for p in (base_dir / ".python_packages" / "lib").glob("python*/site-packages"):
        candidates.append(p)

    for p in candidates:
        if p.exists():
            sp = str(p)
            if sp not in sys.path:
                sys.path.insert(0, sp)
            logging.info(f"Customer site-packages enabled: {sp}")
            return

    logging.warning("Customer site-packages path not found. Imports may fail.")


_ensure_customer_site_packages_on_syspath()

# -----------------------------
# 2) 입력 모드 → ai-agent 플래그 매핑
# -----------------------------
MODE_TO_FLAG = {
    "erd": "--erd",
    "api": "--api",
    "arch": "--arch",
    "ddl": "--ddl",
    "stack": "--stack",
}

# README의 출력 구조(out/) 기준으로 out_dir 하위 파일 경로 매핑
MODE_TO_OUTPUT_FILES = {
    "erd": [
        ("erd/database.dbml", "text/plain"),
        ("erd/erd_summary.md", "text/markdown"),
    ],
    "api": [
        ("api/api_spec.md", "text/markdown"),
    ],
    "arch": [
        ("arch/architecture.md", "text/markdown"),
    ],
    "ddl": [
        ("ddl/schema.sql", "text/plain"),
    ],
    "stack": [
        ("stack/tech_stack.md", "text/markdown"),
    ],
}


def _read_text_file(file_path: Path, max_chars: int = 250_000) -> str:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n... (truncated)"
    return text


def _error(code: str, message: str, details: str = "", status: int = 500) -> func.HttpResponse:
    payload = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details[:20000]
    return func.HttpResponse(
        json.dumps(payload, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
    )


@app.route(route="run", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def run(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("run() called")

    # -----------------------------
    # 요청 파싱
    # -----------------------------
    try:
        body = req.get_json()
        logging.info(f"Request body: {body}")
    except Exception:
        logging.exception("BAD_JSON")
        return _error("BAD_JSON", "Request body must be valid JSON", status=400)

    repo_url = body.get("repo_url")
    mode = (body.get("mode") or "api").lower()

    if not repo_url or not isinstance(repo_url, str):
        return _error("MISSING_REPO_URL", "repo_url is required", status=400)

    if mode not in MODE_TO_FLAG:
        return _error("INVALID_MODE", f"mode must be one of {list(MODE_TO_FLAG.keys())}", status=400)

    flag = MODE_TO_FLAG[mode]

    # -----------------------------
    # 출력 디렉터리 (Functions에서 쓰기 가능한 임시 경로 사용)
    # -----------------------------
    out_dir = Path(tempfile.mkdtemp(prefix="docagent_"))

    # -----------------------------
    # 핵심: subprocess 대신, pyproject.toml의 엔트리포인트를 동일 프로세스에서 직접 호출
    #   ai-agent = "erd_agent.cli:ai_agent" [2](https://www.microsoft.com/en-us/microsoft-365-copilot/microsoft-copilot-studio/)[3](https://learn.microsoft.com/en-us/copilot/microsoft-365/agent-essentials/m365-agents-admin-guide)
    # -----------------------------
    try:
        from erd_agent.cli import ai_agent as ai_agent_entry  # 엔트리포인트 함수
    except Exception as e:
        logging.exception("IMPORT_FAILED erd_agent.cli.ai_agent")
        return _error(
            "IMPORT_FAILED",
            "Cannot import erd_agent. Ensure the package is included in the deployment (.python_packages) and on sys.path.",
            details=str(e),
            status=500,
        )

    # Typer 기반 CLI는 sys.argv를 읽고, 종료 시 SystemExit를 던질 수 있음
    old_argv = sys.argv[:]
    old_env = os.environ.copy()

    try:
        # out_dir를 위치 인자로 넘기거나, 환경변수 DOC_OUTPUT_DIR로도 제어 가능
        # 여기서는 CLI의 Quick Start 형태( repo + out_dir )를 따르되, flag를 앞에 둔다.
        sys.argv = ["ai-agent", flag, repo_url, str(out_dir)]

        # 필요 시 출력 위치를 env로도 고정(코드가 env 우선이면 이게 더 확실)
        # 기존 툴이 DOC_OUTPUT_DIR를 사용한다고 README에 언급되어 있음(기본 ./out)
        os.environ["DOC_OUTPUT_DIR"] = str(out_dir)

        logging.info(f"Invoking ai_agent_entry with argv={sys.argv}")

        try:
            ai_agent_entry()
        except SystemExit as se:
            # Typer는 정상 흐름에서도 SystemExit(0)를 던질 수 있음
            code = se.code if isinstance(se.code, int) else 0
            if code != 0:
                raise RuntimeError(f"ai-agent exited with code {code}") from se

    except Exception as e:
        logging.exception("AGENT_FAILED")
        return _error("AGENT_FAILED", "ai-agent execution failed", details=str(e), status=500)
    finally:
        # 환경 복구
        sys.argv = old_argv
        os.environ.clear()
        os.environ.update(old_env)

    # -----------------------------
    # 산출물 수집
    # -----------------------------
    artifacts = []
    missing = []

    for rel_path, content_type in MODE_TO_OUTPUT_FILES.get(mode, []):
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

    summary = artifacts[0]["content"][:2000] if artifacts else ""

    resp = {
        "status": "ok",
        "repo_url": repo_url,
        "mode": mode,
        "summary": summary,
        "artifacts": artifacts,
        "warnings": [{"missing_files": missing}] if missing else [],
        "logs": {
            "output_dir": str(out_dir),
        },
    }

    return func.HttpResponse(
        json.dumps(resp, ensure_ascii=False),
        status_code=200,
        mimetype="application/json",
    )

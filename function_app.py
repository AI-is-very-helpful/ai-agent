import json
import os
import tempfile
import subprocess
from pathlib import Path
import azure.functions as func

app = func.FunctionApp()

# ai-agent CLI 옵션 매핑 (README 기준) [1](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/build-a-bot)
MODE_TO_FLAG = {
    "erd": "--erd",
    "api": "--api",
    "arch": "--arch",
    "ddl": "--ddl",
    "stack": "--stack",
}

# ai-agent가 out/ 아래에 생성하는 파일 경로 (README 출력 구조 기준) [1](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/build-a-bot)
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
    """
    Functions 응답이 너무 커지는 걸 방지하기 위해 상한을 둡니다.
    (필요하면 늘리거나, URL로 내보내는 구조로 확장 가능)
    """
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n... (truncated)"
    return text

@app.route(route="run", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def run(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/run
    body:
      { "repo_url": "...", "mode": "erd|api|arch|ddl|stack" }
    """
    try:
        body = req.get_json()
    except Exception:
        return func.HttpResponse(
            json.dumps({"error": {"code": "BAD_JSON", "message": "Request body must be valid JSON"}}),
            status_code=400,
            mimetype="application/json",
        )

    repo_url = body.get("repo_url")
    mode = (body.get("mode") or "api").lower()

    if not repo_url or not isinstance(repo_url, str):
        return func.HttpResponse(
            json.dumps({"error": {"code": "MISSING_REPO_URL", "message": "repo_url is required"}}),
            status_code=400,
            mimetype="application/json",
        )

    if mode not in MODE_TO_FLAG:
        return func.HttpResponse(
            json.dumps({
                "error": {
                    "code": "INVALID_MODE",
                    "message": f"mode must be one of {list(MODE_TO_FLAG.keys())}"
                }
            }),
            status_code=400,
            mimetype="application/json",
        )

    # 임시 출력 폴더 생성 (Functions 환경에서 안전한 쓰기 위치)
    out_dir = Path(tempfile.mkdtemp(prefix="docagent_"))

    flag = MODE_TO_FLAG[mode]

    # README 사용법: ai-agent --xxx <repo> <out_dir> [1](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/build-a-bot)
    cmd = ["ai-agent", flag, repo_url, str(out_dir)]

    # 환경 변수(Functions App Settings)로부터 필요한 값은
    # ai-agent 내부에서 읽도록 유지 (AZURE_OPENAI_* 등). [1](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/build-a-bot)
    p = subprocess.run(cmd, capture_output=True, text=True)

    if p.returncode != 0:
        return func.HttpResponse(
            json.dumps({
                "error": {
                    "code": "AGENT_FAILED",
                    "message": "ai-agent execution failed",
                    "details": (p.stderr or p.stdout or "")[:20000]
                }
            }),
            status_code=500,
            mimetype="application/json",
        )

    artifacts = []
    missing = []

    for rel_path, content_type in MODE_TO_OUTPUT_FILES.get(mode, []):
        fpath = out_dir / rel_path
        if fpath.exists():
            artifacts.append({
                "name": fpath.name,
                "path": rel_path,
                "content_type": content_type,
                "content": _read_text_file(fpath)
            })
        else:
            missing.append(rel_path)

    # 간단 요약: markdown 파일이 있으면 첫 파일의 앞부분을 summary로 사용
    summary = ""
    if artifacts:
        summary = artifacts[0]["content"][:2000]

    resp = {
        "status": "ok",
        "repo_url": repo_url,
        "mode": mode,
        "summary": summary,
        "artifacts": artifacts,
        "warnings": [{"missing_files": missing}] if missing else [],
        "logs": {
            "stdout": (p.stdout or "")[:20000],
            "stderr": (p.stderr or "")[:20000],
            "command": " ".join(cmd),
            "output_dir": str(out_dir),
        }
    }

    return func.HttpResponse(
        json.dumps(resp, ensure_ascii=False),
        status_code=200,
        mimetype="application/json",
    )
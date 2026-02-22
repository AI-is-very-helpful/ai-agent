from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse
import hashlib
from git import Repo
from erd_agent.config import settings

def is_git_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://") or s.endswith(".git")

def _safe_repo_dir(url: str) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    name = Path(urlparse(url).path).stem or "repo"
    return f"{name}-{h}"

def prepare_repo(repo: str) -> Path:
    """
    repo가 로컬 경로면 그대로 반환.
    URL이면 cache_dir 아래로 clone/pull 해서 경로 반환.
    """
    p = Path(repo).expanduser()
    if p.exists():
        return p.resolve()

    if not is_git_url(repo):
        raise ValueError("repo는 로컬 경로 또는 https git URL 이어야 합니다.")

    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    target = settings.cache_dir / _safe_repo_dir(repo)

    clone_url = repo
    # Private repo 토큰 사용: https://<token>@github.com/... 같은 방식은 가능하나
    # 여기서는 토큰을 URL에 직접 끼워 넣기보다 사용자가 repo URL 자체에 포함하거나,
    # 환경변수 기반으로 조립하도록 선택 제공.
    if settings.github_token and repo.startswith("https://") and "@" not in repo:
        # token을 URL에 삽입 (주의: 출력/로그 금지)
        # 예시 개념은 “토큰을 https URL에 포함해 clone” 방식과 동일 [10](https://graphite.com/guides/git-clone-with-token)
        clone_url = repo.replace("https://", f"https://{settings.github_token}@")

    if target.exists() and (target / ".git").exists():
        r = Repo(target)
        r.remotes.origin.pull()
        return target.resolve()

    Repo.clone_from(clone_url, target)
    return target.resolve()
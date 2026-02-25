from __future__ import annotations

import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import re

from erd_agent.config import settings


_GH_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)(?:/|$)")


def is_git_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://") or s.endswith(".git")


def _safe_repo_dir(url: str) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    name = Path(urlparse(url).path).stem or "repo"
    # repo.git 형태면 stem이 repo가 되지만, 혹시 방어
    if name.endswith(".git"):
        name = name[:-4]
    return f"{name}-{h}"


def _writable_cache_root() -> Path:
    """
    Azure Functions Linux에서 /home/site/wwwroot 는 read-only일 수 있으니
    cache_dir가 상대경로/점(.) 시작이면 /tmp 아래로 강제한다. [1](https://www.hubsite365.com/en-ww/crm-pages/build-a-custom-api-connector-from-scratch-in-copilot-studio-bbae2a51-393b-498f-9ef4-b6d5a41cb6ee.htm)[2](https://www.youtube.com/watch?v=72YcqlrIM84)
    """
    raw = str(settings.cache_dir) if getattr(settings, "cache_dir", None) else ".cache"
    p = Path(raw)

    # '.cache' 또는 상대 경로면 /tmp 밑으로
    if raw.startswith(".") or not p.is_absolute():
        return Path(tempfile.gettempdir()) / "doc-agent-cache"
    return p


def _github_zip_url(repo_url: str, ref: str) -> str:
    """
    GitHub 공식 소스 아카이브 URL 패턴 사용 [3](https://learn.microsoft.com/en-us/microsoft-copilot-studio/configure-enduser-authentication)
    """
    m = _GH_RE.match(repo_url.strip())
    if not m:
        raise ValueError("Not a GitHub repository URL")
    owner, repo = m.group(1), m.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"https://github.com/{owner}/{repo}/archive/refs/heads/{ref}.zip"


def _download(url: str, dest: Path, token: str | None = None) -> None:
    headers = {"User-Agent": "doc-agent-azure-functions", "Accept": "application/octet-stream"}
    if token:
        # PAT / fine-grained token 이면 보통 Authorization 헤더로 접근
        headers["Authorization"] = f"token {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


def _extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)

    # GitHub zip은 보통 최상위 폴더 1개 생성 (repo-ref 형태)
    subdirs = [p for p in dest_dir.iterdir() if p.is_dir()]
    return subdirs[0] if len(subdirs) == 1 else dest_dir


def prepare_repo(repo: str) -> Path:
    """
    repo가 로컬 경로면 그대로 반환.
    URL이면 cache_dir 아래로 다운로드/압축해제 후 경로 반환.
    - GitHub URL: zip 다운로드(권장, git 불필요)
    - 기타 git URL: git이 PATH에 있을 때만 clone 시도, 없으면 에러
    """
    p = Path(repo).expanduser()
    if p.exists():
        return p.resolve()

    if not is_git_url(repo):
        raise ValueError("repo는 로컬 경로 또는 https git URL 이어야 합니다.")

    cache_root = _writable_cache_root()
    cache_root.mkdir(parents=True, exist_ok=True)
    target = cache_root / _safe_repo_dir(repo)

    # 이미 풀려 있으면 그대로 재사용
    if target.exists():
        return target.resolve()

    # GitHub URL이면 zip 다운로드
    if _GH_RE.match(repo):
        work = Path(tempfile.mkdtemp(prefix="repozip_"))
        zip_path = work / "repo.zip"

        token = getattr(settings, "github_token", None)

        # main → master 순서로 시도 (조직 repo에 따라 기본 브랜치 다름)
        last_err = None
        for ref in ("main", "master"):
            try:
                url = _github_zip_url(repo, ref=ref)
                _download(url, zip_path, token=token)
                src_root = _extract_zip(zip_path, work / "src")

                # target에 이동(atomic하게 하려고 먼저 임시 디렉터리 사용)
                tmp_target = cache_root / (target.name + ".tmp")
                if tmp_target.exists():
                    shutil.rmtree(tmp_target, ignore_errors=True)
                shutil.copytree(src_root, tmp_target)

                tmp_target.replace(target)
                return target.resolve()
            except Exception as e:
                last_err = e
                continue

        raise RuntimeError(f"GitHub zip 다운로드 실패: {last_err}")

    # GitHub가 아닌 git URL: git이 있으면 clone 시도(옵션)
    if shutil.which("git"):
        # git이 있으면 subprocess로 clone (GitPython 의존 제거)
        import subprocess
        clone_url = repo
        if getattr(settings, "github_token", None) and repo.startswith("https://") and "@" not in repo:
            clone_url = repo.replace("https://", f"https://{settings.github_token}@")

        subprocess.run(["git", "clone", "--depth", "1", clone_url, str(target)], check=True)
        return target.resolve()

    raise RuntimeError("이 실행 환경에는 git이 없어서 GitHub URL만 zip 다운로드로 지원합니다.")
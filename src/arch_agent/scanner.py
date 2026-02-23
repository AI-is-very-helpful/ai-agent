"""프로젝트 구조 스캐너 — 아키텍처 파악에 필요한 정보 수집."""
from __future__ import annotations
import re
from pathlib import Path

ARCH_HINTS_RE = re.compile(
    r"@\s*(SpringBootApplication|Configuration|EnableAutoConfiguration"
    r"|Component|Service|Repository|Controller|RestController"
    r"|EnableFeignClients|EnableEurekaClient|EnableDiscoveryClient"
    r"|EnableCircuitBreaker|EnableKafka|EnableCaching"
    r"|EnableJpaRepositories|EnableWebSecurity)\b"
)

CONFIG_FILES = {
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
    "application.yml", "application.yaml", "application.properties",
    "application-dev.yml", "application-prod.yml",
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
    "package.json", "requirements.txt", "go.mod",
}


def scan_arch_files(repo_path: Path) -> list[Path]:
    """아키텍처 파악에 유용한 파일들을 수집한다."""
    candidates: set[Path] = set()

    for f in repo_path.rglob("*"):
        if not f.is_file():
            continue
        if f.name in CONFIG_FILES:
            candidates.add(f)
            continue
        if f.suffix == ".java":
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if ARCH_HINTS_RE.search(text):
                candidates.add(f)

    return sorted(candidates)


def collect_directory_tree(repo_path: Path, max_depth: int = 4) -> str:
    """디렉터리 트리를 문자열로 생성한다 (숨김 폴더, 빌드 산출물 제외)."""
    skip = {".git", "node_modules", "target", "build", ".gradle", ".idea", ".vscode", "__pycache__", ".cache", "out"}
    lines: list[str] = []

    def _walk(p: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        entries = sorted(
            [e for e in p.iterdir() if e.name not in skip and not e.name.startswith(".")],
            key=lambda x: (x.is_file(), x.name),
        )
        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                _walk(entry, prefix + extension, depth + 1)

    lines.append(repo_path.name + "/")
    _walk(repo_path, "", 1)
    return "\n".join(lines)

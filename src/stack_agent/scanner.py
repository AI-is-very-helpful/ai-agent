"""빌드/의존성 파일 스캐너 — 기술 스택 파악용."""
from __future__ import annotations
from pathlib import Path

BUILD_FILES = {
    "pom.xml", "build.gradle", "build.gradle.kts",
    "settings.gradle", "settings.gradle.kts",
    "package.json", "package-lock.json", "yarn.lock",
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile",
    "go.mod", "go.sum",
    "Cargo.toml",
    "Gemfile",
    "Makefile", "CMakeLists.txt",
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
    ".github/workflows/*.yml",
    "application.yml", "application.yaml", "application.properties",
    "application-dev.yml", "application-prod.yml",
    ".env.example", ".env.sample",
}

WORKFLOW_DIR = ".github/workflows"


def scan_stack_files(repo_path: Path) -> list[Path]:
    """빌드·의존성·설정 파일을 수집한다."""
    candidates: set[Path] = set()

    for f in repo_path.rglob("*"):
        if not f.is_file():
            continue
        if f.name in BUILD_FILES:
            candidates.add(f)
        rel = str(f.relative_to(repo_path))
        if rel.startswith(WORKFLOW_DIR) and f.suffix in (".yml", ".yaml"):
            candidates.add(f)

    return sorted(candidates)

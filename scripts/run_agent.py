#!/usr/bin/env python3
"""
ai-agent와 동일한 진입점. README 사용법 그대로 실행 가능.

  python scripts/run_agent.py ./my-project
  python scripts/run_agent.py https://github.com/org/repo.git
  python scripts/run_agent.py --erd --api ./my-project
  python scripts/run_agent.py -e -a -d https://github.com/org/repo.git
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 프로젝트 루트에서 실행 시 src 로드 (pip install 없이 실행 가능)
_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="레포 분석 → ERD, API 스펙, 아키텍처, DDL, 기술 스택 문서 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python scripts/run_agent.py ./my-project
  python scripts/run_agent.py https://github.com/org/repo.git
  python scripts/run_agent.py --erd --api ./my-project
  python scripts/run_agent.py -e -a -d https://github.com/org/repo.git
        """.strip(),
    )
    parser.add_argument("repo", help="로컬 경로 또는 Git URL (예: https://github.com/org/repo.git)")
    parser.add_argument("--erd", "-e", action="store_true", help="ERD 생성 (DBML + 요약 MD)")
    parser.add_argument("--api", "-a", action="store_true", help="API 스펙 문서 생성")
    parser.add_argument("--arch", action="store_true", help="아키텍처 다이어그램 문서 생성")
    parser.add_argument("--ddl", "-d", action="store_true", help="DDL 문서 생성")
    parser.add_argument("--stack", "-s", action="store_true", help="기술 스택 문서 생성")
    parser.add_argument("--use-aoai", action="store_true", help="(ERD) 정적 모드 시 Azure OpenAI 스키마 보정")
    parser.add_argument("--ai-first", action="store_true", help="(ERD) AI-first 모드로 전체 분석")

    args = parser.parse_args()

    any_opt = args.erd or args.api or args.arch or args.ddl or args.stack
    erd = args.erd or not any_opt
    api = args.api or not any_opt
    arch = args.arch or not any_opt
    ddl = args.ddl or not any_opt
    stack = args.stack or not any_opt

    from erd_agent.config import settings
    from erd_agent.commands import erd as cmd_erd
    from api_agent import run_api
    from arch_agent import run_arch
    from ddl_agent import run_ddl
    from stack_agent import run_stack

    base = settings.doc_output_dir
    if not any_opt:
        print("No options given → generating all docs.")

    if erd:
        cmd_erd.run_erd(
            args.repo,
            out_dir=base / "erd",
            use_aoai=args.use_aoai,
            ai_first=args.ai_first,
        )
    if api:
        run_api(args.repo, out_dir=base / "api")
    if arch:
        run_arch(args.repo, out_dir=base / "arch")
    if ddl:
        run_ddl(args.repo, out_dir=base / "ddl")
    if stack:
        run_stack(args.repo, out_dir=base / "stack")

    print(f"Done. Output under {base}")


if __name__ == "__main__":
    main()

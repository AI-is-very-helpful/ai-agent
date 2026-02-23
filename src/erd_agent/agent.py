"""
기존 erd-agent CLI 진입점 (하위 호환).
실제 구현은 erd_agent.cli.erd_app 으로 이동했으며,
pyproject.scripts 에서 erd-agent = "erd_agent.cli:erd_app" 로 등록되어 있습니다.
"""
from __future__ import annotations

from erd_agent.cli import erd_app as app

if __name__ == "__main__":
    app()
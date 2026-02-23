"""기술 스택 분석 결과 → Markdown 문서 생성."""
from __future__ import annotations
from pathlib import Path
from stack_agent.models import ExtractedStack


def to_markdown(stack: ExtractedStack) -> str:
    lines: list[str] = []
    lines.append("# Tech Stack\n")

    if stack.summary:
        lines.append(f"> {stack.summary}\n")

    lines.append("## Overview\n")
    lines.append("| Item | Value |")
    lines.append("|------|-------|")
    if stack.language:
        lines.append(f"| Language | {stack.language} {stack.language_version or ''} |")
    if stack.framework:
        lines.append(f"| Framework | {stack.framework} {stack.framework_version or ''} |")
    if stack.build_tool:
        lines.append(f"| Build tool | {stack.build_tool} |")
    lines.append("")

    for cat in stack.categories:
        lines.append(f"## {cat.category}\n")
        lines.append("| Dependency | Version | Scope | Description |")
        lines.append("|------------|---------|-------|-------------|")
        for item in cat.items:
            lines.append(
                f"| `{item.name}` | {item.version or '-'} | {item.scope or '-'} | {item.description or '-'} |"
            )
        lines.append("")

    return "\n".join(lines)


def write_stack(stack: ExtractedStack, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(to_markdown(stack), encoding="utf-8")
    return out_path

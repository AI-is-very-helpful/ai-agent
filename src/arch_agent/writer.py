"""아키텍처 분석 결과 → Markdown + Mermaid 문서 생성."""
from __future__ import annotations
from pathlib import Path
from arch_agent.models import ExtractedArchitecture


def to_markdown(arch: ExtractedArchitecture) -> str:
    lines: list[str] = []

    title = arch.project_name or "Project"
    lines.append(f"# {title} — Architecture\n")

    if arch.architecture_style:
        lines.append(f"**Architecture style:** {arch.architecture_style}\n")
    if arch.summary:
        lines.append(f"{arch.summary}\n")

    if arch.mermaid_diagram:
        lines.append("## Diagram\n")
        lines.append("```mermaid")
        lines.append(arch.mermaid_diagram)
        lines.append("```\n")

    if arch.layers:
        lines.append("## Layers / Modules\n")
        for layer in arch.layers:
            lines.append(f"### {layer.name}")
            if layer.description:
                lines.append(f"{layer.description}\n")
            if layer.components:
                for comp in layer.components:
                    lines.append(f"- `{comp}`")
                lines.append("")

    if arch.dependencies:
        lines.append("## Dependencies\n")
        lines.append("| Source | Target | Description |")
        lines.append("|--------|--------|-------------|")
        for dep in arch.dependencies:
            lines.append(f"| {dep.source} | {dep.target} | {dep.description or '-'} |")
        lines.append("")

    if arch.external_systems:
        lines.append("## External Systems\n")
        lines.append("| Name | Type | Description |")
        lines.append("|------|------|-------------|")
        for ext in arch.external_systems:
            lines.append(f"| {ext.name} | {ext.type} | {ext.description or '-'} |")
        lines.append("")

    return "\n".join(lines)


def write_architecture(arch: ExtractedArchitecture, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(to_markdown(arch), encoding="utf-8")
    return out_path

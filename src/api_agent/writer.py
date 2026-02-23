"""API 스펙 → Markdown 문서 생성."""
from __future__ import annotations
from pathlib import Path
from api_agent.models import ExtractedApiSpec


def to_markdown(spec: ExtractedApiSpec) -> str:
    lines: list[str] = []
    lines.append("# API Specification\n")

    total_endpoints = sum(len(c.endpoints) for c in spec.controllers)
    lines.append(f"- Controllers: {len(spec.controllers)}")
    lines.append(f"- Total endpoints: {total_endpoints}\n")

    for ctrl in sorted(spec.controllers, key=lambda c: c.name):
        lines.append(f"## {ctrl.name}")
        if ctrl.base_path:
            lines.append(f"**Base path:** `{ctrl.base_path}`\n")
        if ctrl.description:
            lines.append(f"{ctrl.description}\n")

        for ep in ctrl.endpoints:
            tags = f" `{'` `'.join(ep.tags)}`" if ep.tags else ""
            lines.append(f"### `{ep.method}` `{ep.path}`{tags}\n")
            if ep.summary:
                lines.append(f"**{ep.summary}**\n")
            if ep.description:
                lines.append(f"{ep.description}\n")

            if ep.parameters:
                lines.append("| Parameter | Location | Type | Required | Description |")
                lines.append("|-----------|----------|------|----------|-------------|")
                for p in ep.parameters:
                    lines.append(
                        f"| `{p.name}` | {p.location} | {p.type} | "
                        f"{'Yes' if p.required else 'No'} | {p.description or '-'} |"
                    )
                lines.append("")

            if ep.request_body:
                lines.append(f"**Request body:** {ep.request_body}\n")
            if ep.response_body:
                lines.append(f"**Response ({ep.response_status}):** {ep.response_body}\n")

        lines.append("---\n")

    return "\n".join(lines)


def write_api_spec(spec: ExtractedApiSpec, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(to_markdown(spec), encoding="utf-8")
    return out_path

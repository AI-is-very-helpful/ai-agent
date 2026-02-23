"""LLM 기반 아키텍처 분석."""
from __future__ import annotations
import json
from pathlib import Path

from erd_agent.config import settings
from erd_agent.llm.aoai_client import build_aoai_client
from arch_agent.models import ExtractedArchitecture

SYSTEM_PROMPT = """You are a senior software architect.
You analyze project source code and configuration to produce an architecture diagram document.
Return ONLY valid JSON (no markdown, no explanation).
"""

USER_PROMPT_TEMPLATE = """Analyze the following project files and directory structure to produce an architecture overview.

Tasks:
1. Identify the architecture style (Layered, Hexagonal, Microservice, Monolith, etc.)
2. Identify layers/modules and their key components
3. Identify dependencies between layers/modules
4. Identify external systems (databases, caches, message brokers, external APIs)
5. Generate a Mermaid flowchart diagram (graph TD) that visualizes the architecture

Output JSON schema:
{{
  "project_name": "...",
  "architecture_style": "Layered | Microservice | Hexagonal | ...",
  "summary": "One paragraph summary of the architecture",
  "layers": [
    {{
      "name": "Presentation",
      "description": "REST controllers and DTOs",
      "components": ["UserController", "OrderController"]
    }}
  ],
  "dependencies": [
    {{
      "source": "Presentation",
      "target": "Service",
      "description": "Controllers call service layer"
    }}
  ],
  "external_systems": [
    {{
      "name": "MySQL",
      "type": "database",
      "description": "Primary relational database"
    }}
  ],
  "mermaid_diagram": "graph TD\\n  A[Presentation] --> B[Service]\\n  B --> C[Repository]\\n  C --> D[(MySQL)]"
}}

DIRECTORY STRUCTURE:
{dir_tree}

FILES:
{files_blob}
"""


def _make_files_blob(files: list[tuple[Path, str]], max_chars: int = 100_000) -> str:
    parts: list[str] = []
    total = 0
    for p, txt in files:
        if total + len(txt) > max_chars:
            break
        parts.append(f'<file path="{p.as_posix()}">\n{txt}\n</file>')
        total += len(txt)
    return "\n\n".join(parts)


def ai_extract_architecture(
    file_texts: list[tuple[Path, str]],
    dir_tree: str,
) -> ExtractedArchitecture:
    client = build_aoai_client()
    if client is None:
        raise RuntimeError("Azure OpenAI 설정이 없습니다.")

    files_blob = _make_files_blob(file_texts)
    user_prompt = USER_PROMPT_TEMPLATE.format(dir_tree=dir_tree, files_blob=files_blob)

    resp = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)
    return ExtractedArchitecture.model_validate(data)

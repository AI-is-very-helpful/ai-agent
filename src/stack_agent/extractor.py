"""LLM 기반 기술 스택 분석."""
from __future__ import annotations
import json
from pathlib import Path

from erd_agent.config import settings
from erd_agent.llm.aoai_client import build_aoai_client
from stack_agent.models import ExtractedStack

SYSTEM_PROMPT = """You are a senior DevOps engineer and software architect.
You analyze project build/dependency files to produce a comprehensive tech stack document.
Return ONLY valid JSON (no markdown, no explanation).
"""

USER_PROMPT_TEMPLATE = """Analyze the following build/dependency/config files and extract the project tech stack.

Tasks:
1. Identify primary language and version
2. Identify framework and version
3. Identify build tool
4. Categorize all dependencies (Framework, Database, ORM, Testing, Security, Messaging, Cache, CI/CD, DevOps, etc.)
5. Include version for each dependency when available
6. Write a brief summary of the overall tech stack

Output JSON schema:
{{
  "language": "Java",
  "language_version": "17",
  "framework": "Spring Boot",
  "framework_version": "3.2.0",
  "build_tool": "Maven",
  "summary": "Spring Boot 3 microservice with JPA, Kafka, Redis, and PostgreSQL",
  "categories": [
    {{
      "category": "Framework",
      "items": [
        {{"name": "spring-boot-starter-web", "version": "3.2.0", "scope": "compile", "description": "Web MVC framework"}}
      ]
    }},
    {{
      "category": "Database",
      "items": [
        {{"name": "postgresql", "version": "42.7.1", "scope": "runtime", "description": "PostgreSQL JDBC driver"}}
      ]
    }}
  ]
}}

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


def ai_extract_stack(file_texts: list[tuple[Path, str]]) -> ExtractedStack:
    client = build_aoai_client()
    if client is None:
        raise RuntimeError("Azure OpenAI 설정이 없습니다.")

    files_blob = _make_files_blob(file_texts)
    resp = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(files_blob=files_blob)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)
    return ExtractedStack.model_validate(data)

from __future__ import annotations
from dataclasses import dataclass
from erd_agent.config import settings

def build_aoai_client():
    """
    Azure OpenAI가 설정되어 있지 않으면 None 반환.
    """
    if not (settings.azure_openai_endpoint and settings.azure_openai_api_key and settings.azure_openai_deployment):
        return None

    # openai SDK (v1.x) - AzureOpenAI 사용 예시가 공식 예제에 존재 [5](https://github.com/openai/openai-python/blob/main/examples/azure.py)[3](https://developers.openai.com/cookbook/examples/azure/chat)
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.openai_api_version,
    )
    return client
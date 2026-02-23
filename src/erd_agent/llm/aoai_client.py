from __future__ import annotations
from urllib.parse import urlparse
from erd_agent.config import settings


def build_aoai_client():
    """
    Azure OpenAI가 설정되어 있지 않으면 None 반환.
    - 프로젝트 엔드포인트(api/projects): 리소스 루트(호스트 기준)로 AzureOpenAI 사용
    - 엔드포인트가 /openai/v1/ 포함 시: OpenAI(base_url=..., api_key=...) 사용
    - 그 외: AzureOpenAI(azure_endpoint=..., api_key=..., api_version=...) 사용
    """
    if not (settings.azure_openai_endpoint and settings.azure_openai_api_key and settings.azure_openai_deployment):
        return None

    endpoint = settings.azure_openai_endpoint.rstrip("/")

    # 프로젝트 엔드포인트(.services.ai.azure.com): Model Inference API 경로 사용
    if "api/projects" in endpoint:
        parsed = urlparse(endpoint)
        models_base = f"{parsed.scheme}://{parsed.netloc}/models"
        from openai import OpenAI
        # Model Inference API 문서 기준 api-version (리소스별로 다를 수 있음)
        return OpenAI(
            base_url=models_base,
            api_key=settings.azure_openai_api_key,
            default_query={"api-version": "2024-05-01-preview"},
        )

    # /openai/v1/ 형태면 OpenAI 클라이언트로 호출 (배포명을 model로 전달)
    if "/openai/v1" in endpoint:
        from openai import OpenAI
        return OpenAI(base_url=endpoint, api_key=settings.azure_openai_api_key)

    from openai import AzureOpenAI
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.openai_api_version,
    )
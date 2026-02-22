from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    erd_output_dir: Path = Field(default=Path("./out"), alias="ERD_OUTPUT_DIR")
    cache_dir: Path = Field(default=Path("./.cache"), alias="ERD_CACHE_DIR")

    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")

    azure_openai_endpoint: str | None = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str | None = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    openai_api_version: str = Field(default="2024-06-01", alias="OPENAI_API_VERSION")
    azure_openai_deployment: str | None = Field(default=None, alias="AZURE_OPENAI_DEPLOYMENT")

settings = Settings()
# SPDX-License-Identifier: Apache-2.0

import pathlib

import pydantic_settings

_ENV_FILE = pathlib.Path(__file__).resolve().parents[4] / ".env"


class Settings(pydantic_settings.BaseSettings):
    api_base_url: str = "http://localhost:3001"
    api_token: str = "halo-sample-token"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    openai_api_version: str = "2024-12-01-preview"
    log_level: str = "INFO"

    model_config = pydantic_settings.SettingsConfigDict(
        env_file=str(_ENV_FILE),
        extra="ignore",
    )

# SPDX-License-Identifier: Apache-2.0

import pydantic
import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    api_base_url: str = "http://localhost:3001"
    api_token: str = "halo-sample-token"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    openai_api_version: str = "2024-12-01-preview"
    log_level: str = pydantic.Field(
        default="INFO",
        validation_alias="SAMPLE_AGENT_LOG_LEVEL",
    )

    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        populate_by_name=True,
    )

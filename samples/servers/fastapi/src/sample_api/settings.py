# SPDX-License-Identifier: Apache-2.0

import pathlib

import pydantic_settings

_ENV_FILE = pathlib.Path(__file__).resolve().parents[4] / ".env"


class Settings(pydantic_settings.BaseSettings):
    app_title: str = "Sample HALO API"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 3010
    log_level: str = "INFO"

    model_config = pydantic_settings.SettingsConfigDict(
        env_file=str(_ENV_FILE),
        extra="ignore",
    )

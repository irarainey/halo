# SPDX-License-Identifier: Apache-2.0

import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    app_title: str = "Sample HALO API"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 3001

    model_config = {"env_prefix": "SAMPLE_API_"}

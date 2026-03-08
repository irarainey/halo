# SPDX-License-Identifier: Apache-2.0

import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    api_base_url: str = "http://localhost:3001"

    model_config = {"env_prefix": "SAMPLE_AGENT_"}

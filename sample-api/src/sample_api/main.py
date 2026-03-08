# SPDX-License-Identifier: Apache-2.0

from typing import Literal

import fastapi
import pydantic
from fastapi import security as security_mod

from sample_api import settings as settings_mod

settings = settings_mod.Settings()

app = fastapi.FastAPI(title=settings.app_title, version=settings.app_version)

# -- Auth dependency ----------------------------------------------------------

security = security_mod.HTTPBearer()


# -- Models -------------------------------------------------------------------


class GreetRequest(pydantic.BaseModel):
    name: str = pydantic.Field(..., description="Name of the person to greet")
    style: Literal["formal", "casual"] = pydantic.Field("casual", description="Greeting style")

    model_config = pydantic.ConfigDict(json_schema_extra={
        "llm": {
            "why": "Use to generate a greeting for a person. Choose formal for business contexts.",
            "tags": ["greetings", "read"],
        }
    })


class GreetResponse(pydantic.BaseModel):
    message: str


class EchoRequest(pydantic.BaseModel):
    text: str = pydantic.Field(..., description="Text to echo back")

    model_config = pydantic.ConfigDict(json_schema_extra={
        "llm": {
            "why": "Use to echo back arbitrary text. Useful for testing connectivity.",
            "tags": ["debug", "read"],
        }
    })


class EchoResponse(pydantic.BaseModel):
    echo: str


# -- Routes -------------------------------------------------------------------


@app.post("/api/greet", response_model=GreetResponse)
async def greet(body: GreetRequest, token: str = fastapi.Depends(security)):
    """Generate a greeting for the given name."""
    if body.style == "formal":
        return GreetResponse(message=f"Good day, {body.name}.")
    return GreetResponse(message=f"Hey {body.name}!")


@app.post("/api/echo", response_model=EchoResponse)
async def echo(body: EchoRequest, token: str = fastapi.Depends(security)):
    """Echo the provided text back."""
    return EchoResponse(echo=body.text)

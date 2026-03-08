# SPDX-License-Identifier: Apache-2.0

from typing import Literal

import pydantic


class WeatherRequest(pydantic.BaseModel):
    """Request body for the weather lookup endpoint. Accepts a city name."""

    city: str = pydantic.Field(..., description="City name to look up weather for, e.g. 'London', 'Tokyo'")

    model_config = pydantic.ConfigDict(
        json_schema_extra={
            "llm": {
                "why": (
                    "Use to retrieve the current weather conditions and forecast for a city. "
                    "Returns temperature, humidity, wind speed, and a natural-language forecast."
                ),
                "tags": ["weather", "read"],
                "examples": [
                    {
                        "input": {"city": "London"},
                        "output": {"city": "London", "country": "GB", "temperature_c": 12.5, "condition": "overcast"},
                    },
                    {
                        "input": {"city": "Tokyo"},
                        "output": {"city": "Tokyo", "country": "JP", "temperature_c": 18.3, "condition": "sunny"},
                    },
                    {
                        "input": {"city": "Berlin"},
                        "output": {"city": "Berlin", "country": "DE", "temperature_c": 5.2, "condition": "rain"},
                    },
                ],
            }
        }
    )


class WeatherResponse(pydantic.BaseModel):
    """Response containing current weather conditions and forecast for a city."""

    city: str = pydantic.Field(..., description="City name")
    country: str = pydantic.Field(..., description="ISO 3166-1 alpha-2 country code")
    temperature_c: float = pydantic.Field(..., description="Current temperature in degrees Celsius")
    humidity_pct: int = pydantic.Field(..., description="Relative humidity as a percentage (0-100)")
    wind_kph: float = pydantic.Field(..., description="Wind speed in kilometres per hour")
    condition: Literal["sunny", "partly_cloudy", "overcast", "rain", "humid"] = pydantic.Field(..., description="Current weather condition")
    forecast: str = pydantic.Field(..., description="Natural-language forecast summary for the day")

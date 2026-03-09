# SPDX-License-Identifier: Apache-2.0

from typing import Annotated, Any, Literal

import pydantic


def _to_lower(value: Any) -> Any:
    """Normalise string input to lowercase for case-insensitive Literal matching."""
    return value.lower() if isinstance(value, str) else value


class EmployeeLookupRequest(pydantic.BaseModel):
    """Request body for the employee directory lookup. Supports department and office filters."""

    department: Annotated[
        Literal["engineering", "marketing", "finance", "hr", "design", "sales"] | None,
        pydantic.BeforeValidator(_to_lower),
    ] = pydantic.Field(None, description="Optional department filter")
    office: str | None = pydantic.Field(None, description="Optional office location filter, e.g. 'London', 'Berlin'")

    model_config = pydantic.ConfigDict(
        json_schema_extra={
            "llm": {
                "why": (
                    "Use to look up employees in the company directory. "
                    "Filter by department or office location. Returns names, roles, and contact details."
                ),
                "tags": ["employees", "read"],
                "examples": [
                    {
                        "input": {"department": "engineering", "office": "London"},
                        "output": {"employees": [{"name": "Alice Chen", "role": "Senior Software Engineer"}], "total": 2},
                    },
                    {
                        "input": {"department": "marketing"},
                        "output": {"employees": [{"name": "Carol Okafor", "role": "Marketing Manager"}], "total": 1},
                    },
                    {
                        "input": {"office": "Berlin"},
                        "output": {"employees": [{"name": "Eva Johansson", "role": "Engineering Manager"}], "total": 1},
                    },
                ],
            }
        }
    )


class Employee(pydantic.BaseModel):
    """A single employee record from the company directory."""

    employee_id: str = pydantic.Field(..., description="Unique employee identifier")
    name: str = pydantic.Field(..., description="Full name")
    email: str = pydantic.Field(..., description="Work email address")
    department: str = pydantic.Field(..., description="Department name")
    role: str = pydantic.Field(..., description="Job title")
    office: str = pydantic.Field(..., description="Office location")
    start_date: str = pydantic.Field(..., description="Employment start date in ISO 8601 format")


class EmployeeLookupResponse(pydantic.BaseModel):
    """Response containing a filtered list of employees from the company directory."""

    employees: list[Employee] = pydantic.Field(..., description="List of employees matching the filter criteria")
    total: int = pydantic.Field(..., description="Number of employees returned")

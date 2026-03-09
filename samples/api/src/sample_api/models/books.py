# SPDX-License-Identifier: Apache-2.0

from typing import Annotated, Any, Literal

import pydantic


def _to_lower(value: Any) -> Any:
    """Normalise string input to lowercase for case-insensitive Literal matching."""
    return value.lower() if isinstance(value, str) else value


class BookSearchRequest(pydantic.BaseModel):
    """Request body for the book search endpoint. Accepts a search query and optional genre filter."""

    query: str = pydantic.Field(..., description="Search term to match against book titles or author names")
    genre: Annotated[
        Literal["fiction", "non-fiction", "technology"] | None,
        pydantic.BeforeValidator(_to_lower),
    ] = pydantic.Field(None, description="Optional genre filter to narrow results")

    model_config = pydantic.ConfigDict(
        json_schema_extra={
            "llm": {
                "why": (
                    "Use to search the book catalogue by title or author. "
                    "Optionally filter by genre. Returns matching books with summaries and ratings."
                ),
                "tags": ["books", "read"],
                "examples": [
                    {
                        "input": {"query": "Orwell"},
                        "output": {"results": [{"title": "1984", "author": "George Orwell"}], "total": 1},
                    },
                    {
                        "input": {"query": "Pragmatic", "genre": "technology"},
                        "output": {"results": [{"title": "The Pragmatic Programmer", "author": "David Thomas, Andrew Hunt"}], "total": 1},
                    },
                    {
                        "input": {"query": "Harari", "genre": "non-fiction"},
                        "output": {
                            "results": [{"title": "Sapiens: A Brief History of Humankind", "author": "Yuval Noah Harari"}],
                            "total": 1,
                        },
                    },
                ],
            }
        }
    )


class BookResult(pydantic.BaseModel):
    """A single book entry from the catalogue, including metadata and rating."""

    isbn: str = pydantic.Field(..., description="ISBN-13 identifier")
    title: str = pydantic.Field(..., description="Book title")
    author: str = pydantic.Field(..., description="Author name(s)")
    genre: str = pydantic.Field(..., description="Book genre")
    year: int = pydantic.Field(..., description="Year of publication")
    pages: int = pydantic.Field(..., description="Total page count")
    rating: float = pydantic.Field(..., description="Average reader rating out of 5.0")
    summary: str = pydantic.Field(..., description="Brief description of the book")


class BookSearchResponse(pydantic.BaseModel):
    """Response containing a list of books matching the search criteria."""

    results: list[BookResult] = pydantic.Field(..., description="List of books matching the search criteria")
    total: int = pydantic.Field(..., description="Number of results returned")

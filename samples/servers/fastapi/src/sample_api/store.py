# SPDX-License-Identifier: Apache-2.0

"""In-memory data store for the sample API.

Loads initial data from JSON files at import time. POST endpoints append
to the in-memory lists. Data resets on server restart.
"""

from __future__ import annotations

import uuid

from sample_api import data


def _generate_isbn() -> str:
    """Generate a plausible ISBN-13."""
    return f"978-0-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-0"


def _generate_employee_id() -> str:
    """Generate a unique employee ID."""
    return f"EMP-{uuid.uuid4().hex[:6].upper()}"


def _generate_sku(category: str) -> str:
    """Generate a SKU based on category prefix."""
    prefix = category[:2].upper()
    suffix = uuid.uuid4().hex[:4].upper()
    return f"{prefix}-{suffix}"


# In-memory stores — initialised from JSON on first access.
_books: list[dict] | None = None
_employees: list[dict] | None = None
_inventory: list[dict] | None = None


def books() -> list[dict]:
    """Return the in-memory books list, loading from JSON on first call."""
    global _books
    if _books is None:
        _books = data.books()
    return _books


def employees() -> list[dict]:
    """Return the in-memory employees list, loading from JSON on first call."""
    global _employees
    if _employees is None:
        _employees = data.employees()
    return _employees


def inventory() -> list[dict]:
    """Return the in-memory inventory list, loading from JSON on first call."""
    global _inventory
    if _inventory is None:
        _inventory = data.inventory()
    return _inventory

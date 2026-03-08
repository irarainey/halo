# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


def _load(filename: str) -> list[dict]:
    with open(DATA_DIR / filename) as f:
        result: list[dict] = json.load(f)
        return result


def weather() -> list[dict]:
    return _load("weather.json")


def books() -> list[dict]:
    return _load("books.json")


def inventory() -> list[dict]:
    return _load("inventory.json")


def employees() -> list[dict]:
    return _load("employees.json")

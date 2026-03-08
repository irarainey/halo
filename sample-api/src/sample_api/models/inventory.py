# SPDX-License-Identifier: Apache-2.0

from typing import Literal

import pydantic


class InventoryRequest(pydantic.BaseModel):
    """Request body for the inventory check endpoint. Supports category and low-stock filters."""

    category: Literal["electronics", "furniture", "stationery"] | None = pydantic.Field(
        None, description="Optional product category to filter by"
    )
    low_stock_only: bool = pydantic.Field(False, description="When true, return only items at or below their reorder threshold")

    model_config = pydantic.ConfigDict(
        json_schema_extra={
            "llm": {
                "why": (
                    "Use to check current stock levels across warehouses. "
                    "Filter by category or request only low-stock items that may need reordering."
                ),
                "tags": ["inventory", "read"],
                "examples": [
                    {
                        "input": {"low_stock_only": True},
                        "output": {"items": [{"sku": "MN-4022", "name": "27-inch Monitor", "stock": 0}], "total": 2},
                    },
                    {
                        "input": {"category": "electronics"},
                        "output": {"items": [{"sku": "WH-1001", "name": "Wireless Headphones", "stock": 234}], "total": 4},
                    },
                    {
                        "input": {"category": "furniture", "low_stock_only": False},
                        "output": {"items": [{"sku": "CH-3010", "name": "Ergonomic Office Chair", "stock": 12}], "total": 2},
                    },
                ],
            }
        }
    )


class InventoryItem(pydantic.BaseModel):
    """A single product in the warehouse inventory with stock and pricing details."""

    sku: str = pydantic.Field(..., description="Stock-keeping unit identifier")
    name: str = pydantic.Field(..., description="Product name")
    category: str = pydantic.Field(..., description="Product category")
    price_gbp: float = pydantic.Field(..., description="Unit price in GBP")
    stock: int = pydantic.Field(..., description="Current units in stock")
    warehouse: str = pydantic.Field(..., description="Warehouse location holding this stock")
    reorder_threshold: int = pydantic.Field(..., description="Stock level at which reordering is recommended")


class InventoryResponse(pydantic.BaseModel):
    """Response containing a filtered list of inventory items."""

    items: list[InventoryItem] = pydantic.Field(..., description="List of inventory items matching the filter")
    total: int = pydantic.Field(..., description="Number of items returned")

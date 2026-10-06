"""Mock order-management system integration.

Lookups are delegated to each RetailerNode, which reads only its own local
orders. The result exposes only four allowed fields - no retailer ID,
customer ID, order value, address, or order identifier.
"""

from __future__ import annotations

from ..models import SanitizedOrderContext
from ..retailer_nodes.retailer_node import RetailerNode


class MockOrderManagementSystem:
    """Facade over the retailer nodes' local order data."""

    def __init__(self, nodes: list[RetailerNode]) -> None:
        self._nodes = nodes

    def get_sanitized_order_context(self, example_order_id: str) -> SanitizedOrderContext | None:
        """Sanitized context for a local demo order, or None if no node owns it."""
        if not example_order_id or not isinstance(example_order_id, str):
            raise ValueError("example_order_id must be a non-empty string")
        for node in self._nodes:
            ctx = node.get_sanitized_order_context(example_order_id.strip())
            if ctx is not None:
                return ctx
        return None

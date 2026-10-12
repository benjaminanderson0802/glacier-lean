"""Small adapter around the shared test-mode customer block."""

from __future__ import annotations

from typing import Any


DIRECT_BATCH_PLANS = {
    "direct_batch_basic": {"amount": 19, "currency": "USD"},
    "direct_batch_standard": {"amount": 29, "currency": "USD"},
    "direct_batch_plus": {"amount": 49, "currency": "USD"},
}


def _customer_block() -> Any:
    from ventures.blocks import customer
    return customer


def create_direct_checkout(customer_details: dict[str, Any], plan: str) -> dict[str, Any]:
    """Create a test-mode customer record and a fixed-price checkout link."""
    if plan not in DIRECT_BATCH_PLANS:
        raise ValueError("unknown CPSC direct batch plan")
    block = _customer_block()
    customer_record = block.create_customer(customer_details)
    link = block.checkout_link(plan)
    return {"customer": customer_record, "checkout": link, "mode": "test_until_owner_configures_live_key"}


def customer_status_page(customer_id: str) -> Any:
    return _customer_block().status_page(customer_id)


def support_inbox() -> Any:
    return _customer_block().support_inbox()

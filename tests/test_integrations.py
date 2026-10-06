import pytest

from src.integrations import MockCustomerServicePlatform

ALLOWED = {"product_category", "delivery_status", "exchange_available", "return_started"}


def test_sanitized_order_context_fields(service):
    for oid in service.example_order_ids():
        ctx = service.get_sanitized_order_context(oid)
        assert ctx["found"] is True
        assert set(ctx) - {"found"} == ALLOWED
        assert oid not in str(ctx.values())


def test_unknown_order_not_found(service):
    assert service.get_sanitized_order_context("Z-ORD-9999")["found"] is False


def test_support_draft_is_draft_only():
    cs = MockCustomerServicePlatform()
    d = cs.create_support_intervention_draft("COMPATIBILITY", "Recommend compatible replacement",
                                             "Customer support queue")
    assert d.status == "DRAFT"
    assert d.requires_human_approval is True
    assert d.customer_contacted is False
    assert d.message == "Draft created. No customer was contacted."
    assert d.draft_id.startswith("DRAFT-")


def test_support_draft_validation():
    cs = MockCustomerServicePlatform()
    with pytest.raises(ValueError):
        cs.create_support_intervention_draft("NOPE", "x", "y")
    with pytest.raises(ValueError):
        cs.create_support_intervention_draft("DAMAGED", " ", "queue")

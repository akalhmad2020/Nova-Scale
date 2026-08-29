from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.payments.api.schemas import (
    AddPaymentAllocationRequest,
    CreatePaymentRequest,
    PaymentAllocationResponse,
    PaymentResponse,
)
from app.modules.payments.domain.enums import PaymentMethod, PaymentStatus


def test_create_payment_request_accepts_valid_data() -> None:
    customer_id = uuid4()

    request = CreatePaymentRequest(
        customer_id=customer_id,
        payment_number="PAY-001",
        currency="USD",
        amount=Decimal("100.00"),
        method=PaymentMethod.BANK_TRANSFER,
        reference="BANK-REF-001",
        received_at=datetime.now(UTC),
    )

    assert request.customer_id == customer_id
    assert request.payment_number == "PAY-001"
    assert request.currency == "USD"
    assert request.amount == Decimal("100.00")
    assert request.method == PaymentMethod.BANK_TRANSFER
    assert request.reference == "BANK-REF-001"


@pytest.mark.parametrize(
    "payment_number",
    [
        "",
        "   ",
        "\t",
        "\n",
    ],
)
def test_create_payment_request_rejects_blank_payment_number(
    payment_number: str,
) -> None:
    with pytest.raises(ValidationError):
        CreatePaymentRequest(
            customer_id=uuid4(),
            payment_number=payment_number,
            currency="USD",
            amount=Decimal("100.00"),
            method=PaymentMethod.CASH,
        )


@pytest.mark.parametrize(
    "currency",
    [
        "",
        "US",
        "USDD",
        "   ",
    ],
)
def test_create_payment_request_rejects_invalid_currency(
    currency: str,
) -> None:
    with pytest.raises(ValidationError):
        CreatePaymentRequest(
            customer_id=uuid4(),
            payment_number="PAY-001",
            currency=currency,
            amount=Decimal("100.00"),
            method=PaymentMethod.CASH,
        )


@pytest.mark.parametrize(
    "amount",
    [
        Decimal("0.00"),
        Decimal("-0.01"),
        Decimal("-100.00"),
    ],
)
def test_create_payment_request_rejects_non_positive_amount(
    amount: Decimal,
) -> None:
    with pytest.raises(ValidationError):
        CreatePaymentRequest(
            customer_id=uuid4(),
            payment_number="PAY-001",
            currency="USD",
            amount=amount,
            method=PaymentMethod.CASH,
        )


def test_create_payment_request_converts_blank_reference_to_none() -> None:
    request = CreatePaymentRequest(
        customer_id=uuid4(),
        payment_number="PAY-001",
        currency="USD",
        amount=Decimal("100.00"),
        method=PaymentMethod.CASH,
        reference="   ",
    )

    assert request.reference is None


def test_add_payment_allocation_request_accepts_valid_data() -> None:
    invoice_id = uuid4()

    request = AddPaymentAllocationRequest(
        invoice_id=invoice_id,
        amount=Decimal("25.50"),
    )

    assert request.invoice_id == invoice_id
    assert request.amount == Decimal("25.50")


@pytest.mark.parametrize(
    "amount",
    [
        Decimal("0.00"),
        Decimal("-0.01"),
        Decimal("-100.00"),
    ],
)
def test_add_payment_allocation_request_rejects_non_positive_amount(
    amount: Decimal,
) -> None:
    with pytest.raises(ValidationError):
        AddPaymentAllocationRequest(
            invoice_id=uuid4(),
            amount=amount,
        )


def test_payment_response_reads_attributes() -> None:
    now = datetime.now(UTC)

    class PaymentData:
        id = uuid4()
        tenant_id = uuid4()
        customer_id = uuid4()
        payment_number = "PAY-001"
        status = PaymentStatus.DRAFT
        currency = "USD"
        amount = Decimal("100.00")
        method = PaymentMethod.BANK_TRANSFER
        reference = "REF-001"
        received_at = now
        posted_at = None
        created_at = now
        updated_at = now

    response = PaymentResponse.model_validate(PaymentData())

    assert response.id == PaymentData.id
    assert response.status == PaymentStatus.DRAFT
    assert response.amount == Decimal("100.00")
    assert response.method == PaymentMethod.BANK_TRANSFER


def test_payment_allocation_response_reads_attributes() -> None:
    now = datetime.now(UTC)

    class AllocationData:
        id = uuid4()
        tenant_id = uuid4()
        payment_id = uuid4()
        invoice_id = uuid4()
        amount = Decimal("40.00")
        created_at = now
        updated_at = now

    response = PaymentAllocationResponse.model_validate(AllocationData())

    assert response.id == AllocationData.id
    assert response.payment_id == AllocationData.payment_id
    assert response.invoice_id == AllocationData.invoice_id
    assert response.amount == Decimal("40.00")

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.ai.application.agent.shipment_operational_models import (
    ShipmentOperationalIssue,
)
from app.ai.application.agent.shipment_summary_models import (
    ShipmentEventSummary,
    ShipmentSummaryContext,
)
from app.ai.application.services.analyze_shipment_operations import (
    AnalyzeShipmentOperationsService,
)


def make_context(
    *,
    status: str = "in_transit",
    event_count: int = 1,
    latest_event: ShipmentEventSummary | None = None,
    events: tuple[ShipmentEventSummary, ...] | None = None,
    origin_location_id: UUID | None = None,
) -> ShipmentSummaryContext:
    if events is None:
        events = (latest_event,) if latest_event is not None else ()

    resolved_origin_location_id = origin_location_id or uuid4()

    return ShipmentSummaryContext(
        shipment_id=uuid4(),
        tenant_id=uuid4(),
        tracking_number="NS-OPS-001",
        reference="OPS-REF-001",
        status=status,
        service_type="express",
        description="Operational analysis shipment",
        weight=Decimal("10.000"),
        weight_unit="kg",
        notes=None,
        customer_id=uuid4(),
        origin_location_id=resolved_origin_location_id,
        destination_location_id=uuid4(),
        event_count=event_count,
        latest_event=latest_event,
        events=events,
    )


def make_event(
    *,
    occurred_at: datetime,
    status: str | None = "in_transit",
    event_type: str = "picked_up",
    location_id: UUID | None = None,
) -> ShipmentEventSummary:
    return ShipmentEventSummary(
        id=uuid4(),
        event_type=event_type,
        status=status,
        location_id=location_id if location_id is not None else uuid4(),
        description="Operational shipment event",
        occurred_at=occurred_at,
        metadata=None,
    )


def test_analyze_shipment_operations_reports_no_issue_for_recent_in_transit() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    latest_event = make_event(
        occurred_at=now - timedelta(hours=2),
    )

    context = make_context(
        latest_event=latest_event,
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
        now=now,
    )

    assert result.issues == ()
    assert result.has_issues is False
    assert result.highest_severity == "info"
    assert result.risk_score == 0
    assert result.risk_level == "low"


def test_analyze_shipment_operations_detects_stale_in_transit() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    latest_event = make_event(
        occurred_at=now - timedelta(hours=30),
    )

    context = make_context(
        latest_event=latest_event,
    )

    service = AnalyzeShipmentOperationsService(
        stale_in_transit_after=timedelta(hours=24),
    )

    result = service.execute(
        context=context,
        now=now,
    )

    expected_issue = ShipmentOperationalIssue(
        code="stale_in_transit",
        severity="warning",
        message=("Shipment is in transit but has not received a recent operational event."),
        recommended_action=(
            "Verify the shipment's current location and contact "
            "the carrier if no recent tracking update is available."
        ),
        age=timedelta(hours=30),
    )

    assert expected_issue in result.issues

    issue = result.issues[0]

    assert issue.code == "stale_in_transit"
    assert issue.severity == "warning"
    assert issue.age == timedelta(hours=30)
    assert "contact the carrier" in issue.recommended_action

    assert result.has_issues is True
    assert result.highest_severity == "warning"
    assert result.risk_score == 25
    assert result.risk_level == "medium"


def test_analyze_shipment_operations_detects_stalled_at_location() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    latest_event = make_event(
        occurred_at=now - timedelta(hours=14),
        event_type="arrived_at_location",
    )

    context = make_context(
        latest_event=latest_event,
    )

    service = AnalyzeShipmentOperationsService(
        stalled_at_location_after=timedelta(hours=12),
    )

    result = service.execute(
        context=context,
        now=now,
    )

    issue = next(issue for issue in result.issues if issue.code == "stalled_at_location")

    assert issue.severity == "warning"
    assert issue.age == timedelta(hours=14)
    assert "planned departure" in issue.recommended_action
    assert result.risk_score == 25
    assert result.risk_level == "medium"


def test_operational_risk_becomes_high_for_multiple_warnings() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    latest_event = make_event(
        occurred_at=now - timedelta(hours=30),
        event_type="arrived_at_location",
    )

    context = make_context(
        latest_event=latest_event,
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
        now=now,
    )

    codes = {issue.code for issue in result.issues}

    assert "stale_in_transit" in codes
    assert "stalled_at_location" in codes
    assert result.risk_score == 50
    assert result.risk_level == "high"


def test_analyze_shipment_operations_detects_in_transit_without_events() -> None:
    context = make_context(
        status="in_transit",
        event_count=0,
        latest_event=None,
        events=(),
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
    )

    codes = {issue.code for issue in result.issues}

    assert "in_transit_without_events" in codes
    assert "missing_timeline" in codes

    in_transit_issue = next(
        issue for issue in result.issues if issue.code == "in_transit_without_events"
    )

    assert in_transit_issue.severity == "critical"
    assert in_transit_issue.age is None
    assert "obtain the latest tracking information" in in_transit_issue.recommended_action

    missing_timeline_issue = next(
        issue for issue in result.issues if issue.code == "missing_timeline"
    )

    assert missing_timeline_issue.severity == "warning"
    assert missing_timeline_issue.age is None
    assert "shipment events are being received" in missing_timeline_issue.recommended_action

    assert result.has_issues is True
    assert result.highest_severity == "critical"
    assert result.risk_score == 85
    assert result.risk_level == "critical"


def test_analyze_shipment_operations_allows_draft_without_timeline() -> None:
    context = make_context(
        status="draft",
        event_count=0,
        latest_event=None,
        events=(),
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
    )

    assert result.issues == ()
    assert result.has_issues is False
    assert result.risk_score == 0
    assert result.risk_level == "low"


def test_analyze_shipment_operations_detects_delivered_status_mismatch() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    latest_event = make_event(
        occurred_at=now,
        status="in_transit",
        event_type="arrived_at_location",
    )

    context = make_context(
        status="delivered",
        latest_event=latest_event,
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
        now=now,
    )

    issue = next(
        issue for issue in result.issues if issue.code == "delivered_status_without_delivered_event"
    )

    assert issue.severity == "warning"
    assert issue.age is None
    assert "Verify the delivery confirmation" in issue.recommended_action
    assert result.highest_severity == "warning"


def test_analyze_shipment_operations_accepts_matching_delivered_event() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    latest_event = make_event(
        occurred_at=now,
        status="delivered",
        event_type="status_changed",
    )

    context = make_context(
        status="delivered",
        latest_event=latest_event,
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
        now=now,
    )

    assert result.issues == ()
    assert result.has_issues is False
    assert result.highest_severity == "info"


def test_analyze_shipment_operations_detects_cancelled_status_mismatch() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    latest_event = make_event(
        occurred_at=now,
        status="in_transit",
        event_type="picked_up",
    )

    context = make_context(
        status="cancelled",
        latest_event=latest_event,
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
        now=now,
    )

    issue = next(
        issue for issue in result.issues if issue.code == "cancelled_status_without_cancelled_event"
    )

    assert issue.severity == "warning"
    assert issue.age is None
    assert "Verify the cancellation record" in issue.recommended_action
    assert result.highest_severity == "warning"


def test_analyze_shipment_operations_accepts_matching_cancelled_event() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    latest_event = make_event(
        occurred_at=now,
        status="cancelled",
        event_type="status_changed",
    )

    context = make_context(
        status="cancelled",
        latest_event=latest_event,
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
        now=now,
    )

    assert result.issues == ()
    assert result.has_issues is False
    assert result.highest_severity == "info"


def test_analyze_shipment_operations_detects_terminal_status_regression() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    delivered_event = make_event(
        occurred_at=now - timedelta(hours=2),
        status="delivered",
        event_type="status_changed",
    )

    regressed_event = make_event(
        occurred_at=now - timedelta(hours=1),
        status="in_transit",
        event_type="status_changed",
    )

    context = make_context(
        status="in_transit",
        event_count=2,
        latest_event=regressed_event,
        events=(
            delivered_event,
            regressed_event,
        ),
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
        now=now,
    )

    issue = next(issue for issue in result.issues if issue.code == "terminal_status_regression")

    assert issue.severity == "critical"
    assert issue.age == timedelta(hours=1)
    assert "correct the shipment timeline" in issue.recommended_action
    assert result.highest_severity == "critical"
    assert result.risk_score == 60
    assert result.risk_level == "critical"


def test_analyze_shipment_operations_detects_departure_without_recorded_arrival() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    origin_location_id = uuid4()
    hub_location_id = uuid4()

    departure_event = make_event(
        occurred_at=now - timedelta(hours=3),
        event_type="departed_location",
        location_id=hub_location_id,
    )

    context = make_context(
        origin_location_id=origin_location_id,
        latest_event=departure_event,
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
        now=now,
    )

    issue = next(
        issue for issue in result.issues if issue.code == "departure_without_recorded_arrival"
    )

    assert issue.severity == "warning"
    assert issue.age == timedelta(hours=3)
    assert "arrival event is missing" in issue.recommended_action


def test_analyze_shipment_operations_allows_origin_departure_without_arrival() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    origin_location_id = uuid4()

    departure_event = make_event(
        occurred_at=now - timedelta(hours=3),
        event_type="departed_location",
        location_id=origin_location_id,
    )

    context = make_context(
        origin_location_id=origin_location_id,
        latest_event=departure_event,
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
        now=now,
    )

    assert not any(issue.code == "departure_without_recorded_arrival" for issue in result.issues)


def test_operational_analysis_prioritizes_critical_issue() -> None:
    context = make_context(
        status="in_transit",
        event_count=0,
        latest_event=None,
        events=(),
    )

    service = AnalyzeShipmentOperationsService()

    result = service.execute(
        context=context,
    )

    assert result.has_issues is True
    assert result.highest_severity == "critical"
    assert result.risk_level == "critical"

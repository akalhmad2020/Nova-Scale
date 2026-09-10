from datetime import UTC, datetime, timedelta

from app.ai.application.agent.shipment_operational_models import (
    ShipmentOperationalAnalysis,
    ShipmentOperationalIssue,
)
from app.ai.application.agent.shipment_summary_models import (
    ShipmentSummaryContext,
)


class AnalyzeShipmentOperationsService:
    def __init__(
        self,
        *,
        stale_in_transit_after: timedelta = timedelta(hours=24),
        stalled_at_location_after: timedelta = timedelta(hours=12),
    ) -> None:
        self._stale_in_transit_after = stale_in_transit_after
        self._stalled_at_location_after = stalled_at_location_after

    def execute(
        self,
        *,
        context: ShipmentSummaryContext,
        now: datetime | None = None,
    ) -> ShipmentOperationalAnalysis:
        current_time = now or datetime.now(UTC)

        issues: list[ShipmentOperationalIssue] = []

        issues.extend(
            self._detect_stale_in_transit(
                context=context,
                now=current_time,
            )
        )

        issues.extend(
            self._detect_stalled_at_location(
                context=context,
                now=current_time,
            )
        )

        issues.extend(
            self._detect_missing_timeline(
                context=context,
            )
        )

        issues.extend(
            self._detect_status_timeline_mismatch(
                context=context,
            )
        )

        issues.extend(
            self._detect_terminal_status_regression(
                context=context,
                now=current_time,
            )
        )

        issues.extend(
            self._detect_departure_without_arrival(
                context=context,
                now=current_time,
            )
        )

        return ShipmentOperationalAnalysis(
            issues=tuple(issues),
        )

    def _detect_stale_in_transit(
        self,
        *,
        context: ShipmentSummaryContext,
        now: datetime,
    ) -> tuple[ShipmentOperationalIssue, ...]:
        if context.status != "in_transit":
            return ()

        latest_event = context.latest_event

        if latest_event is None:
            return (
                ShipmentOperationalIssue(
                    code="in_transit_without_events",
                    severity="critical",
                    message=("Shipment is in transit but has no recorded shipment events."),
                    recommended_action=(
                        "Verify the shipment status and obtain the latest "
                        "tracking information from the carrier."
                    ),
                ),
            )

        age = now - latest_event.occurred_at

        if age <= self._stale_in_transit_after:
            return ()

        return (
            ShipmentOperationalIssue(
                code="stale_in_transit",
                severity="warning",
                message=("Shipment is in transit but has not received a recent operational event."),
                recommended_action=(
                    "Verify the shipment's current location and contact "
                    "the carrier if no recent tracking update is available."
                ),
                age=age,
            ),
        )

    def _detect_stalled_at_location(
        self,
        *,
        context: ShipmentSummaryContext,
        now: datetime,
    ) -> tuple[ShipmentOperationalIssue, ...]:
        if context.status != "in_transit":
            return ()

        latest_event = context.latest_event

        if latest_event is None:
            return ()

        if latest_event.event_type != "arrived_at_location":
            return ()

        if latest_event.location_id is None:
            return ()

        age = now - latest_event.occurred_at

        if age <= self._stalled_at_location_after:
            return ()

        return (
            ShipmentOperationalIssue(
                code="stalled_at_location",
                severity="warning",
                message=(
                    "Shipment arrived at a location but no later operational "
                    "event indicates that it departed or progressed."
                ),
                recommended_action=(
                    "Check whether the shipment is on hold at the location "
                    "and confirm the planned departure with the carrier."
                ),
                age=age,
            ),
        )

    @staticmethod
    def _detect_missing_timeline(
        *,
        context: ShipmentSummaryContext,
    ) -> tuple[ShipmentOperationalIssue, ...]:
        if context.event_count > 0:
            return ()

        if context.status == "draft":
            return ()

        return (
            ShipmentOperationalIssue(
                code="missing_timeline",
                severity="warning",
                message=(
                    "Shipment has progressed beyond draft status "
                    "without any recorded timeline events."
                ),
                recommended_action=(
                    "Verify that shipment events are being received "
                    "and recorded from the operational or carrier source."
                ),
            ),
        )

    @staticmethod
    def _detect_status_timeline_mismatch(
        *,
        context: ShipmentSummaryContext,
    ) -> tuple[ShipmentOperationalIssue, ...]:
        latest_event = context.latest_event

        if latest_event is None:
            return ()

        if context.status == "delivered":
            if latest_event.status == "delivered":
                return ()

            return (
                ShipmentOperationalIssue(
                    code="delivered_status_without_delivered_event",
                    severity="warning",
                    message=(
                        "Shipment is marked as delivered but the latest "
                        "timeline event does not confirm delivered status."
                    ),
                    recommended_action=(
                        "Verify the delivery confirmation and reconcile "
                        "the shipment status with its timeline."
                    ),
                ),
            )

        if context.status == "cancelled":
            if latest_event.status == "cancelled":
                return ()

            return (
                ShipmentOperationalIssue(
                    code="cancelled_status_without_cancelled_event",
                    severity="warning",
                    message=(
                        "Shipment is marked as cancelled but the latest "
                        "timeline event does not confirm cancelled status."
                    ),
                    recommended_action=(
                        "Verify the cancellation record and reconcile "
                        "the shipment status with its timeline."
                    ),
                ),
            )

        return ()

    @staticmethod
    def _detect_terminal_status_regression(
        *,
        context: ShipmentSummaryContext,
        now: datetime,
    ) -> tuple[ShipmentOperationalIssue, ...]:
        terminal_status: str | None = None

        for event in sorted(
            context.events,
            key=lambda item: item.occurred_at,
        ):
            event_status = event.status

            if terminal_status is None:
                if event_status in {
                    "delivered",
                    "cancelled",
                }:
                    terminal_status = event_status

                continue

            if event_status is None or event_status == terminal_status:
                continue

            return (
                ShipmentOperationalIssue(
                    code="terminal_status_regression",
                    severity="critical",
                    message=(
                        f"Shipment timeline moved from terminal status "
                        f"'{terminal_status}' to '{event_status}'."
                    ),
                    recommended_action=(
                        "Review the conflicting status events and correct "
                        "the shipment timeline before further automation."
                    ),
                    age=now - event.occurred_at,
                ),
            )

        return ()

    @staticmethod
    def _detect_departure_without_arrival(
        *,
        context: ShipmentSummaryContext,
        now: datetime,
    ) -> tuple[ShipmentOperationalIssue, ...]:
        arrived_location_ids = set()

        for event in sorted(
            context.events,
            key=lambda item: item.occurred_at,
        ):
            if event.location_id is None:
                continue

            if event.event_type == "arrived_at_location":
                arrived_location_ids.add(event.location_id)
                continue

            if event.event_type != "departed_location":
                continue

            if event.location_id == context.origin_location_id:
                continue

            if event.location_id in arrived_location_ids:
                continue

            return (
                ShipmentOperationalIssue(
                    code="departure_without_recorded_arrival",
                    severity="warning",
                    message=(
                        "Shipment timeline contains a departure from a "
                        "non-origin location without a prior recorded arrival "
                        "at that location."
                    ),
                    recommended_action=(
                        "Reconcile the carrier event sequence and verify "
                        "whether an arrival event is missing from the timeline."
                    ),
                    age=now - event.occurred_at,
                ),
            )

        return ()

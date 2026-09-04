export type ShipmentEventType =
  | "created"
  | "status_changed"
  | "picked_up"
  | "arrived_at_location"
  | "departed_location"
  | "note_added";

export type ShipmentEventStatus =
  | "draft"
  | "ready"
  | "in_transit"
  | "delivered"
  | "cancelled";

export type ShipmentEvent = {
  id: string;
  tenant_id: string;
  shipment_id: string;

  event_type: ShipmentEventType;
  status: ShipmentEventStatus | null;

  location_id: string | null;
  description: string | null;
  occurred_at: string;

  metadata: Record<string, unknown> | null;

  created_by_user_id: string | null;

  created_at: string;
  updated_at: string;
};

export type RecordShipmentEventInput = {
  event_type: ShipmentEventType;
  occurred_at: string;
  status?: ShipmentEventStatus | null;
  location_id?: string | null;
  description?: string | null;
  metadata?: Record<string, unknown> | null;
};
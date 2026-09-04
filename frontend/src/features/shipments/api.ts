import type { ShipmentEvent , RecordShipmentEventInput, } from "@/features/shipments/events-types";
import type {
  CreateShipmentInput,
  Shipment,
  TransitionShipmentStatusInput,
} from "@/features/shipments/types";


export async function getShipments(): Promise<
  Shipment[]
> {
  const response = await fetch(
    "/api/shipments",
    {
      method: "GET",
      cache: "no-store",
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Unable to load shipments",
    );
  }

  return data as Shipment[];
}

export async function createShipment(
  input: CreateShipmentInput,
): Promise<Shipment> {
  const response = await fetch(
    "/api/shipments",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Unable to create shipment",
    );
  }

  return data as Shipment;
}

export async function getShipment(
  shipmentId: string,
): Promise<Shipment> {
  const response = await fetch(
    `/api/shipments/${shipmentId}`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Unable to load shipment",
    );
  }

  return data as Shipment;
}

export async function getShipmentEvents(
  shipmentId: string,
): Promise<ShipmentEvent[]> {
  const response = await fetch(
    `/api/shipments/${shipmentId}/events`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Unable to load shipment events",
    );
  }

  return data as ShipmentEvent[];
}

export async function recordShipmentEvent(
  shipmentId: string,
  input: RecordShipmentEventInput,
): Promise<ShipmentEvent> {
  const response = await fetch(
    `/api/shipments/${shipmentId}/events`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Unable to record shipment event",
    );
  }

  return data as ShipmentEvent;
}

export async function transitionShipmentStatus(
  shipmentId: string,
  input: TransitionShipmentStatusInput,
): Promise<Shipment> {
  const response = await fetch(
    `/api/shipments/${shipmentId}/transition`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Unable to transition shipment status",
    );
  }

  return data as Shipment;
}
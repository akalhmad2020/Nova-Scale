export type ShipmentStatus =
  | "draft"
  | "ready"
  | "in_transit"
  | "delivered"
  | "cancelled";

export type ServiceType =
  | "standard"
  | "express";

export type WeightUnit =
  | "kg"
  | "lb";

export type Shipment = {
  id: string;
  tenant_id: string;

  customer_id: string;
  origin_location_id: string;
  destination_location_id: string;

  tracking_number: string;
  reference: string | null;

  status: ShipmentStatus;
  service_type: ServiceType;

  description: string | null;

  weight: string;
  weight_unit: WeightUnit;

  notes: string | null;

  created_at: string;
  updated_at: string;
};

export type CreateShipmentInput = {
  customer_id: string;
  origin_location_id: string;
  destination_location_id: string;

  tracking_number: string;
  reference: string | null;

  service_type: ServiceType;

  description: string | null;

  weight: string;
  weight_unit: WeightUnit;

  notes: string | null;
};

export type UpdateShipmentInput =
  CreateShipmentInput;

export type TransitionShipmentStatusInput = {
  status: ShipmentStatus;
};
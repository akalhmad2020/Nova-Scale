export type LocationStatus =
  | "active"
  | "inactive";

export type LocationType =
  | "warehouse"
  | "office"
  | "store"
  | "pickup"
  | "delivery"
  | "other";

export type Location = {
  id: string;
  tenant_id: string;

  name: string;
  code: string;
  type: LocationType;

  contact_name: string | null;
  email: string | null;
  phone: string | null;

  country_code: string;
  state: string | null;
  city: string;
  postal_code: string | null;

  address_line1: string;
  address_line2: string | null;

  latitude: string | null;
  longitude: string | null;

  status: LocationStatus;
  notes: string | null;

  created_at: string;
  updated_at: string;
};

export type CreateLocationInput = {
  name: string;
  code: string;
  type: LocationType;

  country_code: string;
  state: string | null;
  city: string;
  postal_code: string | null;

  address_line1: string;
  address_line2: string | null;

  contact_name: string | null;
  email: string | null;
  phone: string | null;

  latitude: string | null;
  longitude: string | null;

  notes: string | null;
};
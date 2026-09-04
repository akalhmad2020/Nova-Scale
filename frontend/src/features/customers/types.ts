export type CustomerStatus =
  | "active"
  | "inactive";

export type Customer = {
  id: string;
  tenant_id: string;

  name: string;
  code: string;

  email: string | null;
  phone: string | null;

  status: CustomerStatus;

  notes: string | null;

  created_at: string;
  updated_at: string;
};

export type CreateCustomerInput = {
  name: string;
  code: string;
  email: string | null;
  phone: string | null;
  notes: string | null;
};
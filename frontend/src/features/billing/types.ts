export type InvoiceStatus =
  | "draft"
  | "issued"
  | "paid"
  | "void";

export type Invoice = {
  id: string;
  tenant_id: string;
  customer_id: string;

  invoice_number: string;
  status: InvoiceStatus;
  currency: string;

  subtotal: string;
  tax_amount: string;
  total_amount: string;

  issued_at: string | null;
  due_at: string | null;
  paid_at: string | null;

  created_at: string;
  updated_at: string;
};

export type InvoiceLine = {
  id: string;
  tenant_id: string;
  invoice_id: string;
  shipment_id: string | null;

  description: string;
  quantity: string;
  unit_price: string;
  amount: string;

  created_at: string;
  updated_at: string;
};

export type CreateInvoiceInput = {
  customer_id: string;
  invoice_number: string;
  currency: string;
  tax_amount: string;
};

export type AddInvoiceLineInput = {
  shipment_id: string | null;
  description: string;
  quantity: string;
  unit_price: string;
};
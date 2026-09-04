import type {
  AddInvoiceLineInput,
  CreateInvoiceInput,
  Invoice,
  InvoiceLine,
} from "@/features/billing/types";

export async function getInvoices(): Promise<Invoice[]> {
  const response = await fetch("/api/invoices");

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to load invoices",
      ),
    );
  }

  return response.json();
}

export async function createInvoice(
  input: CreateInvoiceInput,
): Promise<Invoice> {
  const response = await fetch("/api/invoices", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to create invoice",
      ),
    );
  }

  return response.json();
}

export async function getInvoice(
  invoiceId: string,
): Promise<Invoice> {
  const response = await fetch(
    `/api/invoices/${invoiceId}`,
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to load invoice",
      ),
    );
  }

  return response.json();
}

export async function getInvoiceLines(
  invoiceId: string,
): Promise<InvoiceLine[]> {
  const response = await fetch(
    `/api/invoices/${invoiceId}/lines`,
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to load invoice lines",
      ),
    );
  }

  return response.json();
}

export async function addInvoiceLine(
  invoiceId: string,
  input: AddInvoiceLineInput,
): Promise<InvoiceLine> {
  const response = await fetch(
    `/api/invoices/${invoiceId}/lines`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to add invoice line",
      ),
    );
  }

  return response.json();
}

async function getErrorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body = (await response.json()) as {
      detail?: string;
    };

    return body.detail ?? fallback;
  } catch {
    return fallback;
  }
}

export async function removeInvoiceLine(
  invoiceId: string,
  invoiceLineId: string,
): Promise<void> {
  const response = await fetch(
    `/api/invoices/${invoiceId}/lines/${invoiceLineId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to remove invoice line",
      ),
    );
  }
}

export async function issueInvoice(
  invoiceId: string,
): Promise<Invoice> {
  const response = await fetch(
    `/api/invoices/${invoiceId}/issue`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to issue invoice",
      ),
    );
  }

  return response.json();
}

export async function voidInvoice(
  invoiceId: string,
): Promise<Invoice> {
  const response = await fetch(
    `/api/invoices/${invoiceId}/void`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to void invoice",
      ),
    );
  }

  return response.json();
}
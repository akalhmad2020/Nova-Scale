import type {
  CreateCustomerInput,
  Customer,
} from "@/features/customers/types";

export async function getCustomers(): Promise<
  Customer[]
> {
  const response = await fetch(
    "/api/customers",
    {
      method: "GET",
      cache: "no-store",
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Unable to load customers",
    );
  }

  return data as Customer[];
}

export async function createCustomer(
  input: CreateCustomerInput,
): Promise<Customer> {
  const response = await fetch(
    "/api/customers",
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
        "Unable to create customer",
    );
  }

  return data as Customer;
}
import { z } from "zod";

export const createInvoiceSchema = z.object({
  customer_id: z
    .string()
    .min(1, "Customer is required"),

  invoice_number: z
    .string()
    .trim()
    .min(1, "Invoice number is required")
    .max(
      50,
      "Invoice number must be at most 50 characters",
    ),

  currency: z
    .string()
    .trim()
    .length(
      3,
      "Currency must be a 3-letter code",
    ),

  tax_amount: z
    .string()
    .trim()
    .min(1, "Tax amount is required")
    .refine(
      (value) => {
        const amount = Number(value);

        return (
          Number.isFinite(amount) &&
          amount >= 0
        );
      },
      {
        message:
          "Tax amount must be zero or greater",
      },
    ),
});

export type CreateInvoiceFormValues =
  z.infer<typeof createInvoiceSchema>;
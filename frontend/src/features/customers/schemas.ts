import { z } from "zod";

export const createCustomerSchema = z.object({
  name: z
    .string()
    .min(1, "Customer name is required")
    .max(
      200,
      "Customer name must be at most 200 characters",
    ),

  code: z
    .string()
    .min(1, "Customer code is required")
    .max(
      100,
      "Customer code must be at most 100 characters",
    ),

  email: z
    .string()
    .email("Enter a valid email address")
    .or(z.literal("")),

  phone: z
    .string()
    .max(
      50,
      "Phone must be at most 50 characters",
    )
    .optional(),

  notes: z.string().optional(),
});

export type CreateCustomerFormValues =
  z.infer<typeof createCustomerSchema>;
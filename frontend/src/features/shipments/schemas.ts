import { z } from "zod";

export const createShipmentSchema = z.object({
  customer_id: z
    .string()
    .min(1, "Customer is required"),

  origin_location_id: z
    .string()
    .min(1, "Origin location is required"),

  destination_location_id: z
    .string()
    .min(1, "Destination location is required"),

  tracking_number: z
    .string()
    .min(1, "Tracking number is required")
    .max(
      100,
      "Tracking number must be at most 100 characters",
    ),

  reference: z
    .string()
    .max(
      150,
      "Reference must be at most 150 characters",
    )
    .optional(),

  service_type: z.enum([
    "standard",
    "express",
  ]),

  description: z
    .string()
    .max(
      500,
      "Description must be at most 500 characters",
    )
    .optional(),

  weight: z
    .string()
    .min(1, "Weight is required")
    .refine(
      (value) => {
        const parsed = Number(value);

        return (
          Number.isFinite(parsed) &&
          parsed > 0
        );
      },
      {
        message:
          "Weight must be greater than zero",
      },
    ),

  weight_unit: z.enum([
    "kg",
    "lb",
  ]),

  notes: z.string().optional(),
});

export type CreateShipmentFormValues =
  z.infer<typeof createShipmentSchema>;
import { z } from "zod";

export const createLocationSchema = z.object({
  name: z
    .string()
    .min(1, "Location name is required")
    .max(
      200,
      "Location name must be at most 200 characters",
    ),

  code: z
    .string()
    .min(1, "Location code is required")
    .max(
      100,
      "Location code must be at most 100 characters",
    ),

  type: z.enum([
    "warehouse",
    "office",
    "store",
    "pickup",
    "delivery",
    "other",
  ]),

  country_code: z
    .string()
    .length(
      2,
      "Country code must contain exactly 2 characters",
    ),

  state: z
    .string()
    .max(
      150,
      "State must be at most 150 characters",
    )
    .optional(),

  city: z
    .string()
    .min(1, "City is required")
    .max(
      150,
      "City must be at most 150 characters",
    ),

  postal_code: z
    .string()
    .max(
      32,
      "Postal code must be at most 32 characters",
    )
    .optional(),

  address_line1: z
    .string()
    .min(1, "Address is required")
    .max(
      300,
      "Address must be at most 300 characters",
    ),

  address_line2: z
    .string()
    .max(
      300,
      "Address line 2 must be at most 300 characters",
    )
    .optional(),

  contact_name: z
    .string()
    .max(
      200,
      "Contact name must be at most 200 characters",
    )
    .optional(),

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

  latitude: z
    .string()
    .refine(
      (value) =>
        value === "" ||
        (
          Number.isFinite(Number(value)) &&
          Number(value) >= -90 &&
          Number(value) <= 90
        ),
      {
        message:
          "Latitude must be between -90 and 90",
      },
    ),

  longitude: z
    .string()
    .refine(
      (value) =>
        value === "" ||
        (
          Number.isFinite(Number(value)) &&
          Number(value) >= -180 &&
          Number(value) <= 180
        ),
      {
        message:
          "Longitude must be between -180 and 180",
      },
    ),

  notes: z.string().optional(),
});

export type CreateLocationFormValues =
  z.infer<typeof createLocationSchema>;
import { z } from "zod";

export const createTenantSchema = z.object({
  name: z
    .string()
    .min(1, "Tenant name is required")
    .max(200, "Tenant name must be at most 200 characters"),

  slug: z
    .string()
    .min(1, "Tenant slug is required")
    .max(100, "Tenant slug must be at most 100 characters")
    .regex(
      /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
      "Use lowercase letters, numbers, and hyphens only",
    ),
});

export type CreateTenantFormValues = z.infer<
  typeof createTenantSchema
>;
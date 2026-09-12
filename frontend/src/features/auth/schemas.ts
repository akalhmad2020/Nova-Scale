import { z } from "zod";

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, "Email is required")
    .email("Enter a valid email address"),

  password: z
    .string()
    .min(1, "Password is required")
    .max(128, "Password must be at most 128 characters"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

const workspaceSlugPattern = /^[\p{L}\p{N}]+(?:-[\p{L}\p{N}]+)*$/u;

export const registerSchema = z
  .object({
    first_name: z
      .string()
      .trim()
      .min(1, "First name is required")
      .max(100, "First name must be at most 100 characters"),

    last_name: z
      .string()
      .trim()
      .min(1, "Last name is required")
      .max(100, "Last name must be at most 100 characters"),

    email: z
      .string()
      .trim()
      .min(1, "Email is required")
      .email("Enter a valid email address"),

    company_name: z
      .string()
      .trim()
      .min(1, "Company name is required")
      .max(200, "Company name must be at most 200 characters"),

    plan_code: z.enum(["starter", "professional"]),

    company_slug: z
      .string()
      .trim()
      .min(1, "Workspace identifier is required")
      .max(100, "Workspace identifier must be at most 100 characters")
      .regex(
        workspaceSlugPattern,
        "Use letters, numbers, and single hyphens only",
      ),

    password: z
      .string()
      .min(12, "Password must be at least 12 characters")
      .max(128, "Password must be at most 128 characters"),

    confirm_password: z
      .string()
      .min(1, "Confirm your password")
      .max(128, "Password must be at most 128 characters"),
  })
  .refine((values) => values.password === values.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export type RegisterFormValues = z.infer<typeof registerSchema>;

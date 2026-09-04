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

export const registerSchema = z.object({
  email: z
    .string()
    .min(1, "Email is required")
    .email("Enter a valid email address"),

  password: z
    .string()
    .min(12, "Password must be at least 12 characters")
    .max(128, "Password must be at most 128 characters"),

  first_name: z
    .string()
    .min(1, "First name is required")
    .max(100, "First name must be at most 100 characters"),

  last_name: z
    .string()
    .min(1, "Last name is required")
    .max(100, "Last name must be at most 100 characters"),
});

export type RegisterFormValues = z.infer<typeof registerSchema>;
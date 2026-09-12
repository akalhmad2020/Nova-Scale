import "server-only";

import { z } from "zod";

const envSchema = z.object({
  BACKEND_API_BASE_URL: z.string().url(),
});

export const env = envSchema.parse({
  BACKEND_API_BASE_URL: process.env.BACKEND_API_BASE_URL,
});

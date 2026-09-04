import { useMutation } from "@tanstack/react-query";

import { runAgent } from "@/features/ai/api";
import type {
  AgentRequest,
  AgentResponse,
} from "@/features/ai/types";

export function useRunAgent() {
  return useMutation<
    AgentResponse,
    Error,
    AgentRequest
  >({
    mutationFn: runAgent,
  });
}
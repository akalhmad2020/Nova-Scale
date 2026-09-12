import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  cancelAgentAction,
  confirmAgentAction,
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  runAgent,
} from "@/features/ai/api";
import type {
  AgentActionMutationResponse,
  AgentRequest,
  AgentResponse,
} from "@/features/ai/types";
import { useActiveTenantId } from "@/features/tenants/active-hooks";
import {
  canRunTenantScopedQuery,
  getResolvedActiveTenantId,
  requireActiveTenantId,
} from "@/features/tenants/query-state";

const conversationKeys = {
  all: (tenantId: string) =>
    ["ai", "conversations", tenantId] as const,
  detail: (
    tenantId: string,
    conversationId: string,
  ) =>
    [
      "ai",
      "conversations",
      tenantId,
      conversationId,
    ] as const,
};

export function useRunAgent() {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation<
    AgentResponse,
    Error,
    AgentRequest
  >({
    mutationFn: runAgent,
    onSuccess: async (_data, variables) => {
      const tenantId = activeTenantIdQuery.data;

      if (!tenantId) {
        return;
      }

      await queryClient.invalidateQueries({
        queryKey: conversationKeys.all(tenantId),
      });

      if (variables.conversation_id) {
        await queryClient.invalidateQueries({
          queryKey: conversationKeys.detail(
            tenantId,
            variables.conversation_id,
          ),
        });
      }
    },
  });
}

export function useConfirmAgentAction() {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation<
    AgentActionMutationResponse,
    Error,
    string
  >({
    mutationFn: confirmAgentAction,
    onSuccess: async () => {
      const tenantId = activeTenantIdQuery.data;

      if (!tenantId) {
        return;
      }

      await queryClient.invalidateQueries({
        queryKey: conversationKeys.all(tenantId),
      });
    },
  });
}

export function useCancelAgentAction() {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation<
    AgentActionMutationResponse,
    Error,
    string
  >({
    mutationFn: cancelAgentAction,
    onSuccess: async () => {
      const tenantId = activeTenantIdQuery.data;

      if (!tenantId) {
        return;
      }

      await queryClient.invalidateQueries({
        queryKey: conversationKeys.all(tenantId),
      });
    },
  });
}

export function useAIConversations() {
  const activeTenantIdQuery = useActiveTenantId();
  const tenantId = getResolvedActiveTenantId(
    activeTenantIdQuery,
  );

  return useQuery({
    queryKey: tenantId
      ? conversationKeys.all(tenantId)
      : ["ai", "conversations", "inactive"],
    queryFn: () => {
      requireActiveTenantId(activeTenantIdQuery);
      return listConversations();
    },
    enabled: canRunTenantScopedQuery(activeTenantIdQuery),
    retry: false,
  });
}

export function useAIConversation(
  conversationId: string | null,
) {
  const activeTenantIdQuery = useActiveTenantId();
  const tenantId = getResolvedActiveTenantId(
    activeTenantIdQuery,
  );

  return useQuery({
    queryKey:
      tenantId && conversationId
        ? conversationKeys.detail(
            tenantId,
            conversationId,
          )
        : ["ai", "conversations", "inactive", "none"],
    queryFn: () => {
      requireActiveTenantId(activeTenantIdQuery);

      if (!conversationId) {
        throw new Error("Conversation id is required");
      }

      return getConversation(conversationId);
    },
    enabled:
      Boolean(conversationId) &&
      canRunTenantScopedQuery(activeTenantIdQuery),
    retry: false,
  });
}

export function useCreateAIConversation() {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: createConversation,
    onSuccess: async () => {
      const tenantId = activeTenantIdQuery.data;

      if (!tenantId) {
        return;
      }

      await queryClient.invalidateQueries({
        queryKey: conversationKeys.all(tenantId),
      });
    },
  });
}

export function useDeleteAIConversation() {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: deleteConversation,
    onSuccess: async () => {
      const tenantId = activeTenantIdQuery.data;

      if (!tenantId) {
        return;
      }

      await queryClient.invalidateQueries({
        queryKey: conversationKeys.all(tenantId),
      });
    },
  });
}

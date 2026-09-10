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

const conversationKeys = {
  all: ["ai", "conversations"] as const,
  detail: (conversationId: string) =>
    ["ai", "conversations", conversationId] as const,
};

export function useRunAgent() {
  const queryClient = useQueryClient();

  return useMutation<
    AgentResponse,
    Error,
    AgentRequest
  >({
    mutationFn: runAgent,
    onSuccess: async (_data, variables) => {
      await queryClient.invalidateQueries({
        queryKey: conversationKeys.all,
      });

      if (variables.conversation_id) {
        await queryClient.invalidateQueries({
          queryKey: conversationKeys.detail(
            variables.conversation_id,
          ),
        });
      }
    },
  });
}

export function useConfirmAgentAction() {
  const queryClient = useQueryClient();

  return useMutation<
    AgentActionMutationResponse,
    Error,
    string
  >({
    mutationFn: confirmAgentAction,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: conversationKeys.all,
      });
    },
  });
}

export function useCancelAgentAction() {
  const queryClient = useQueryClient();

  return useMutation<
    AgentActionMutationResponse,
    Error,
    string
  >({
    mutationFn: cancelAgentAction,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: conversationKeys.all,
      });
    },
  });
}

export function useAIConversations() {
  return useQuery({
    queryKey: conversationKeys.all,
    queryFn: listConversations,
  });
}

export function useAIConversation(
  conversationId: string | null,
) {
  return useQuery({
    queryKey: conversationId
      ? conversationKeys.detail(conversationId)
      : ["ai", "conversations", "none"],
    queryFn: () => {
      if (!conversationId) {
        throw new Error("Conversation id is required");
      }

      return getConversation(conversationId);
    },
    enabled: Boolean(conversationId),
  });
}

export function useCreateAIConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createConversation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: conversationKeys.all,
      });
    },
  });
}

export function useDeleteAIConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteConversation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: conversationKeys.all,
      });
    },
  });
}

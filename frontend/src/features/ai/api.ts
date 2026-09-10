import type {
  AgentRequest,
  AgentResponse,
  AIConversationDetail,
  AIConversationSummary,
} from "@/features/ai/types";

async function getErrorMessage(
  response: Response,
): Promise<string> {
  try {
    const body = (await response.json()) as {
      detail?: string;
    };

    return body.detail ?? "Request failed";
  } catch {
    return "Request failed";
  }
}

async function requireOk(
  response: Response,
): Promise<Response> {
  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response),
    );
  }

  return response;
}

export async function runAgent(
  input: AgentRequest,
): Promise<AgentResponse> {
  const response = await requireOk(
    await fetch("/api/ai/agent", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    }),
  );

  return (await response.json()) as AgentResponse;
}

export async function createConversation(): Promise<AIConversationDetail> {
  const response = await requireOk(
    await fetch("/api/ai/conversations", {
      method: "POST",
    }),
  );

  return (await response.json()) as AIConversationDetail;
}

export async function listConversations(): Promise<AIConversationSummary[]> {
  const response = await requireOk(
    await fetch("/api/ai/conversations", {
      method: "GET",
      cache: "no-store",
    }),
  );

  return (await response.json()) as AIConversationSummary[];
}

export async function getConversation(
  conversationId: string,
): Promise<AIConversationDetail> {
  const response = await requireOk(
    await fetch(
      `/api/ai/conversations/${conversationId}`,
      {
        method: "GET",
        cache: "no-store",
      },
    ),
  );

  return (await response.json()) as AIConversationDetail;
}

export async function deleteConversation(
  conversationId: string,
): Promise<void> {
  await requireOk(
    await fetch(
      `/api/ai/conversations/${conversationId}`,
      {
        method: "DELETE",
      },
    ),
  );
}

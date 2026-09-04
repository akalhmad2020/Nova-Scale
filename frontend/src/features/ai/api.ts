import type {
  AgentRequest,
  AgentResponse,
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

export async function runAgent(
  input: AgentRequest,
): Promise<AgentResponse> {
  const response = await fetch(
    "/api/ai/agent",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response),
    );
  }

  return (await response.json()) as AgentResponse;
}
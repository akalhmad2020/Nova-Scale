export type ShipmentContinuationRoute =
  | "get_shipment"
  | "summarize_shipment"
  | "analyze_shipment_operations";

export type AgentContinuation = {
  kind: "shipment_selection";
  route: ShipmentContinuationRoute;
  original_identifier: string;
};

export type ConversationRole =
  | "user"
  | "assistant";

export type AgentRequest = {
  question: string;
  conversation_id?: string | null;
  continuation?: AgentContinuation | null;
};

export type AgentResponse = {
  answer: string;
  continuation?: AgentContinuation | null;
};

export type AIConversationSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type AIConversationMessage = {
  id: string;
  role: ConversationRole;
  content: string;
  created_at: string;
};

export type AIConversationDetail = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: AIConversationMessage[];
  continuation?: AgentContinuation | null;
};

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

export type AgentConversationMessage = {
  role: ConversationRole;
  content: string;
};

export type AgentConversationContext = {
  messages: AgentConversationMessage[];
};

export type AgentRequest = {
  question: string;
  continuation?: AgentContinuation | null;
  conversation_context?: AgentConversationContext | null;
};

export type AgentResponse = {
  answer: string;
  continuation?: AgentContinuation | null;
};
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

export type AgentActionType =
  | "transition_shipment_status"
  | "update_shipment_notes";

export type AgentActionStatus =
  | "pending_confirmation"
  | "executing"
  | "executed"
  | "cancelled"
  | "failed";

export type AgentAction = {
  id: string;
  action_type: AgentActionType;
  status: AgentActionStatus;
  resource_type: string;
  resource_id: string;
  shipment_identifier: string;
  summary: string;
  expected_status: string;
  target_status?: string | null;
  new_notes?: string | null;
  result_summary?: string | null;
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentRequest = {
  question: string;
  conversation_id?: string | null;
  continuation?: AgentContinuation | null;
};

export type AgentResponse = {
  answer: string;
  continuation?: AgentContinuation | null;
};

export type AgentActionMutationResponse = {
  answer: string;
  action: AgentAction;
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
  pending_action?: AgentAction | null;
};

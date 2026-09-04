export type AgentRequest = {
  question: string;
};

export type AgentResponse = {
  answer: string;
};

export type AskQuestionRequest = {
  question: string;
  limit?: number;
};

export type RAGSource = {
  document_id: string;
  chunk_index: number;
  content: string;
  score: number;
};

export type AskQuestionResponse = {
  content: string;
  model: string;
  sources: RAGSource[];
};
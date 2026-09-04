"use client";

import { FormEvent, useState } from "react";

import { useRunAgent } from "@/features/ai/hooks";

type ConversationMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
};

export function AIAssistantContent() {
  const [question, setQuestion] =
    useState("");

  const [messages, setMessages] =
    useState<ConversationMessage[]>([]);

  const agentMutation =
    useRunAgent();

  function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalizedQuestion =
      question.trim();

    if (
      !normalizedQuestion ||
      agentMutation.isPending
    ) {
      return;
    }

    const userMessage: ConversationMessage =
      {
        id: Date.now(),
        role: "user",
        content:
          normalizedQuestion,
      };

    setMessages((current) => [
      ...current,
      userMessage,
    ]);

    setQuestion("");

    agentMutation.mutate(
      {
        question:
          normalizedQuestion,
      },
      {
        onSuccess: (data) => {
          const assistantMessage: ConversationMessage =
            {
              id:
                Date.now() + 1,
              role: "assistant",
              content:
                data.answer,
            };

          setMessages(
            (current) => [
              ...current,
              assistantMessage,
            ],
          );
        },
      },
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">
          AI Assistant
        </h1>

        <p className="mt-1 text-sm text-gray-600">
          Ask NovaScale about your
          shipments and indexed
          knowledge.
        </p>
      </div>

      {messages.length > 0 && (
        <div className="space-y-4">
          {messages.map(
            (message) => (
              <div
                key={message.id}
                className={
                  message.role ===
                  "user"
                    ? "ml-auto max-w-2xl rounded-lg bg-black p-4 text-white"
                    : "mr-auto max-w-2xl rounded-lg border border-gray-200 bg-white p-4"
                }
              >
                <div className="mb-2 text-xs font-semibold uppercase opacity-60">
                  {message.role ===
                  "user"
                    ? "You"
                    : "NovaScale AI"}
                </div>

                <div className="whitespace-pre-wrap text-sm leading-6">
                  {
                    message.content
                  }
                </div>
              </div>
            ),
          )}
        </div>
      )}

      {agentMutation.isPending && (
        <div className="mr-auto max-w-2xl rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-sm text-gray-500">
            NovaScale AI is
            thinking...
          </div>
        </div>
      )}

      {agentMutation.isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {
            agentMutation.error
              .message
          }
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="space-y-4"
      >
        <div>
          <label
            htmlFor="question"
            className="block text-sm font-medium"
          >
            Question
          </label>

          <textarea
            id="question"
            value={question}
            onChange={(event) =>
              setQuestion(
                event.target.value,
              )
            }
            rows={4}
            maxLength={4000}
            placeholder="Ask about a shipment or your indexed documents..."
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
          />
        </div>

        <button
          type="submit"
          disabled={
            agentMutation.isPending ||
            !question.trim()
          }
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {agentMutation.isPending
            ? "Thinking..."
            : "Ask"}
        </button>
      </form>
    </div>
  );
}
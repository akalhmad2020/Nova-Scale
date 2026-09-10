"use client";

import {
  FormEvent,
  useState,
} from "react";

import {
  useAIConversation,
  useAIConversations,
  useCancelAgentAction,
  useConfirmAgentAction,
  useCreateAIConversation,
  useDeleteAIConversation,
  useRunAgent,
} from "@/features/ai/hooks";
import type {
  AgentContinuation,
  AIConversationMessage,
} from "@/features/ai/types";

type LocalMessage = Pick<
  AIConversationMessage,
  "id" | "role" | "content"
>;

export function AIAssistantContent() {
  const [question, setQuestion] =
    useState("");

  const [
    conversationId,
    setConversationId,
  ] = useState<string | null>(null);

  const [
    optimisticMessage,
    setOptimisticMessage,
  ] = useState<LocalMessage | null>(null);

  const [
    localContinuation,
    setLocalContinuation,
  ] = useState<AgentContinuation | null>(
    null,
  );

  const conversationsQuery =
    useAIConversations();

  const conversationQuery =
    useAIConversation(
      conversationId,
    );

  const createConversationMutation =
    useCreateAIConversation();

  const deleteConversationMutation =
    useDeleteAIConversation();

  const confirmActionMutation =
    useConfirmAgentAction();

  const cancelActionMutation =
    useCancelAgentAction();

  const agentMutation = useRunAgent();

  const pendingAction =
    conversationQuery.data?.pending_action ??
    null;

  const isPending =
    agentMutation.isPending ||
    createConversationMutation.isPending ||
    deleteConversationMutation.isPending ||
    confirmActionMutation.isPending ||
    cancelActionMutation.isPending;

  const persistedMessages =
    conversationQuery.data?.messages ?? [];

  const messages: LocalMessage[] =
    optimisticMessage
      ? [
          ...persistedMessages,
          optimisticMessage,
        ]
      : persistedMessages;

  const continuation =
    localContinuation ??
    conversationQuery.data?.continuation ??
    null;

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalizedQuestion =
      question.trim();

    if (
      !normalizedQuestion ||
      isPending ||
      pendingAction
    ) {
      return;
    }

    let activeConversationId =
      conversationId;

    if (!activeConversationId) {
      const created =
        await createConversationMutation.mutateAsync();

      activeConversationId = created.id;

      setConversationId(
        created.id,
      );

      setLocalContinuation(null);
    }

    const pendingMessage: LocalMessage = {
      id: `pending-${Date.now()}`,
      role: "user",
      content: normalizedQuestion,
    };

    setOptimisticMessage(
      pendingMessage,
    );

    setQuestion("");

    try {
      const data =
        await agentMutation.mutateAsync({
          question: normalizedQuestion,
          conversation_id:
            activeConversationId,
          continuation,
        });

      setLocalContinuation(
        data.continuation ?? null,
      );

      setOptimisticMessage(null);
    } catch {
      setOptimisticMessage(null);
    }
  }

  function startNewConversation() {
    setConversationId(null);
    setOptimisticMessage(null);
    setLocalContinuation(null);
    setQuestion("");

    agentMutation.reset();
    confirmActionMutation.reset();
    cancelActionMutation.reset();
  }

  function selectConversation(
    selectedConversationId: string,
  ) {
    if (isPending) {
      return;
    }

    setConversationId(
      selectedConversationId,
    );

    setOptimisticMessage(null);
    setLocalContinuation(null);

    agentMutation.reset();
    confirmActionMutation.reset();
    cancelActionMutation.reset();
  }

  async function removeConversation(
    selectedConversationId: string,
  ) {
    if (isPending) {
      return;
    }

    await deleteConversationMutation.mutateAsync(
      selectedConversationId,
    );

    if (
      conversationId ===
      selectedConversationId
    ) {
      startNewConversation();
    }
  }

  function cancelClarification() {
    setLocalContinuation(null);
  }

  async function confirmPendingAction() {
    if (
      !pendingAction ||
      pendingAction.status !==
        "pending_confirmation" ||
      isPending
    ) {
      return;
    }

    await confirmActionMutation.mutateAsync(
      pendingAction.id,
    );

    agentMutation.reset();
  }

  async function cancelPendingAction() {
    if (
      !pendingAction ||
      pendingAction.status !==
        "pending_confirmation" ||
      isPending
    ) {
      return;
    }

    await cancelActionMutation.mutateAsync(
      pendingAction.id,
    );

    agentMutation.reset();
  }

  const requestError =
    agentMutation.error ??
    createConversationMutation.error ??
    deleteConversationMutation.error ??
    confirmActionMutation.error ??
    cancelActionMutation.error ??
    conversationQuery.error ??
    conversationsQuery.error;

  return (
    <div className="grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
      <aside className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
        <button
          type="button"
          onClick={
            startNewConversation
          }
          disabled={isPending}
          className="w-full rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          New conversation
        </button>

        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Conversations
          </div>

          {conversationsQuery.isLoading && (
            <p className="text-sm text-gray-500">
              Loading conversations...
            </p>
          )}

          {!conversationsQuery.isLoading &&
            conversationsQuery.data
              ?.length === 0 && (
              <p className="text-sm text-gray-500">
                No saved conversations yet.
              </p>
            )}

          <div className="space-y-2">
            {conversationsQuery.data?.map(
              (conversation) => (
                <div
                  key={conversation.id}
                  className={
                    conversation.id ===
                    conversationId
                      ? "rounded-md border border-black bg-gray-50 p-2"
                      : "rounded-md border border-gray-200 p-2"
                  }
                >
                  <button
                    type="button"
                    onClick={() =>
                      selectConversation(
                        conversation.id,
                      )
                    }
                    disabled={isPending}
                    className="block w-full truncate text-left text-sm font-medium disabled:cursor-not-allowed"
                    title={
                      conversation.title
                    }
                  >
                    {
                      conversation.title
                    }
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      void removeConversation(
                        conversation.id,
                      )
                    }
                    disabled={isPending}
                    className="mt-2 text-xs text-gray-500 hover:text-red-600 disabled:cursor-not-allowed"
                  >
                    Delete
                  </button>
                </div>
              ),
            )}
          </div>
        </div>
      </aside>

      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">
            AI Assistant
          </h1>

          <p className="mt-1 text-sm text-gray-600">
            Ask NovaScale about your
            shipments and indexed
            knowledge. Write actions are
            always shown for confirmation
            before execution.
          </p>
        </div>

        {conversationQuery.isLoading &&
          conversationId && (
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-500">
              Loading conversation...
            </div>
          )}

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
                    {message.content}
                  </div>
                </div>
              ),
            )}
          </div>
        )}

        {continuation?.kind ===
          "shipment_selection" && (
          <div className="max-w-2xl rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            NovaScale is waiting for a
            tracking number or shipment
            UUID to continue the previous
            request for{" "}
            <strong>
              {
                continuation.original_identifier
              }
            </strong>
            .
          </div>
        )}

        {pendingAction && (
          <div className="max-w-2xl space-y-3 rounded-lg border border-amber-300 bg-amber-50 p-4">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                Action requires confirmation
              </div>

              <p className="mt-2 text-sm font-medium text-amber-950">
                {pendingAction.summary}
              </p>
            </div>

            <dl className="grid gap-2 text-sm text-amber-900 sm:grid-cols-2">
              <div>
                <dt className="font-medium">
                  Shipment
                </dt>
                <dd>
                  {
                    pendingAction.shipment_identifier
                  }
                </dd>
              </div>

              <div>
                <dt className="font-medium">
                  Status
                </dt>
                <dd>
                  {pendingAction.status}
                </dd>
              </div>

              {pendingAction.target_status && (
                <div>
                  <dt className="font-medium">
                    Transition
                  </dt>
                  <dd>
                    {
                      pendingAction.expected_status
                    }{" "}
                    →{" "}
                    {
                      pendingAction.target_status
                    }
                  </dd>
                </div>
              )}

              {pendingAction.new_notes && (
                <div className="sm:col-span-2">
                  <dt className="font-medium">
                    Proposed notes
                  </dt>
                  <dd className="whitespace-pre-wrap">
                    {pendingAction.new_notes}
                  </dd>
                </div>
              )}
            </dl>

            {pendingAction.status ===
              "pending_confirmation" && (
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() =>
                    void confirmPendingAction()
                  }
                  disabled={isPending}
                  className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {confirmActionMutation.isPending
                    ? "Executing..."
                    : "Confirm action"}
                </button>

                <button
                  type="button"
                  onClick={() =>
                    void cancelPendingAction()
                  }
                  disabled={isPending}
                  className="rounded-md border border-amber-400 bg-white px-4 py-2 text-sm font-medium text-amber-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Cancel action
                </button>
              </div>
            )}

            {pendingAction.status ===
              "executing" && (
              <p className="text-sm text-amber-800">
                This action is already being
                executed. New messages are
                blocked until its state is
                resolved.
              </p>
            )}
          </div>
        )}

        {agentMutation.isPending && (
          <div className="mr-auto max-w-2xl rounded-lg border border-gray-200 bg-white p-4">
            <div className="text-sm text-gray-500">
              NovaScale AI is thinking...
            </div>
          </div>
        )}

        {requestError && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {requestError.message}
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
              {pendingAction
                ? "Pending action"
                : continuation
                  ? "Shipment identifier"
                  : "Question"}
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
              disabled={Boolean(pendingAction)}
              placeholder={
                pendingAction
                  ? "Confirm or cancel the pending action before continuing..."
                  : continuation
                    ? "Enter the tracking number or shipment UUID..."
                    : "Ask about a shipment or request a supported shipment action..."
              }
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 disabled:cursor-not-allowed disabled:bg-gray-100"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={
                isPending ||
                Boolean(pendingAction) ||
                !question.trim()
              }
              className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {agentMutation.isPending
                ? "Thinking..."
                : continuation
                  ? "Continue"
                  : "Ask"}
            </button>

            {continuation &&
              !pendingAction && (
              <button
                type="button"
                onClick={
                  cancelClarification
                }
                disabled={isPending}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
              >
                Cancel clarification
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

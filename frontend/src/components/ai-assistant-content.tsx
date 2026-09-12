"use client";

import {
  FormEvent,
  type ReactNode,
  useRef,
  useState,
} from "react";
import {
  usePathname,
  useRouter,
  useSearchParams,
} from "next/navigation";

import { PlanAccessCard } from "@/components/plan-access-card";
import { Icon } from "@/components/ui/icon";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
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
import {
  hasAIAssistantAccess,
  resolveCurrentPlan,
} from "@/features/saas/access";
import {
  useCurrentSubscription,
  usePlans,
} from "@/features/saas/hooks";

type LocalMessage = Pick<
  AIConversationMessage,
  "id" | "role" | "content"
>;

export function AIAssistantContent() {
  const plansQuery = usePlans();
  const subscriptionQuery = useCurrentSubscription();

  if (plansQuery.isPending || subscriptionQuery.isPending) {
    return (
      <AIPageFrame>
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Checking workspace plan access...
        </div>
      </AIPageFrame>
    );
  }

  if (plansQuery.isError || subscriptionQuery.isError) {
    return (
      <AIPageFrame>
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
          Unable to verify AI access for this workspace. Review the subscription page or refresh the page.
        </div>
      </AIPageFrame>
    );
  }

  const currentPlan = resolveCurrentPlan(
    plansQuery.data,
    subscriptionQuery.data,
  );

  if (!currentPlan) {
    return (
      <AIPageFrame>
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
          The current workspace plan is not present in the plan catalog.
        </div>
      </AIPageFrame>
    );
  }

  if (!currentPlan.entitlements.ai_assistant) {
    return (
      <AIPageFrame>
        <PlanAccessCard
          eyebrow="Plan upgrade"
          currentPlanName={currentPlan.name}
          title="NovaScale AI is available on Professional"
          description="Upgrade the workspace plan to unlock shipment intelligence, RAG-backed operational context, and controlled AI actions with explicit confirmation."
        />
      </AIPageFrame>
    );
  }

  if (
    !hasAIAssistantAccess(
      currentPlan,
      subscriptionQuery.data,
    )
  ) {
    return (
      <AIPageFrame>
        <PlanAccessCard
          eyebrow="Subscription status"
          currentPlanName={currentPlan.name}
          title="NovaScale AI access is currently paused"
          description={`The ${currentPlan.name} plan includes NovaScale AI, but this workspace subscription is ${subscriptionQuery.data.status.replaceAll("_", " ")}.`}
        />
      </AIPageFrame>
    );
  }

  return <AIWorkspace />;
}

function AIPageFrame({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Operational copilot"
        title="NovaScale AI"
        description="Investigate shipments, use indexed operational context, and prepare controlled write actions that always require explicit confirmation."
        actions={
          <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600">
            Plan-aware access
          </div>
        }
      />
      {children}
    </div>
  );
}

function AIWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [question, setQuestion] = useState("");
  const [optimisticMessage, setOptimisticMessage] = useState<LocalMessage | null>(null);
  const [localContinuation, setLocalContinuation] = useState<AgentContinuation | null>(null);

  const optimisticMessageSequence = useRef(0);

  const conversationId = searchParams.get("conversation");

  const conversationsQuery = useAIConversations();
  const conversationQuery = useAIConversation(conversationId);
  const createConversationMutation = useCreateAIConversation();
  const deleteConversationMutation = useDeleteAIConversation();
  const confirmActionMutation = useConfirmAgentAction();
  const cancelActionMutation = useCancelAgentAction();
  const agentMutation = useRunAgent();

  const pendingAction = conversationQuery.data?.pending_action ?? null;
  const isPending =
    agentMutation.isPending ||
    createConversationMutation.isPending ||
    deleteConversationMutation.isPending ||
    confirmActionMutation.isPending ||
    cancelActionMutation.isPending;

  const persistedMessages = conversationQuery.data?.messages ?? [];
  const messages: LocalMessage[] = optimisticMessage
    ? [...persistedMessages, optimisticMessage]
    : persistedMessages;

  const continuation =
    localContinuation ?? conversationQuery.data?.continuation ?? null;

  function setConversationId(nextConversationId: string | null) {
    const params = new URLSearchParams(searchParams.toString());

    if (nextConversationId) {
      params.set("conversation", nextConversationId);
    } else {
      params.delete("conversation");
    }

    const query = params.toString();

    router.replace(
      query ? `${pathname}?${query}` : pathname,
      { scroll: false },
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuestion = question.trim();

    if (!normalizedQuestion || isPending || pendingAction) {
      return;
    }

    resetMutationErrors();

    let activeConversationId = conversationId;

    try {
      if (!activeConversationId) {
        const created =
          await createConversationMutation.mutateAsync();
        activeConversationId = created.id;
        setConversationId(created.id);
        setLocalContinuation(null);
      }

      optimisticMessageSequence.current += 1;

      setOptimisticMessage({
        id: `pending-${optimisticMessageSequence.current}`,
        role: "user",
        content: normalizedQuestion,
      });
      setQuestion("");

      const data = await agentMutation.mutateAsync({
        question: normalizedQuestion,
        conversation_id: activeConversationId,
        continuation,
      });

      setLocalContinuation(data.continuation ?? null);
      setOptimisticMessage(null);
    } catch {
      setOptimisticMessage(null);
      setQuestion(normalizedQuestion);
    }
  }

  function resetMutationErrors() {
    agentMutation.reset();
    createConversationMutation.reset();
    deleteConversationMutation.reset();
    confirmActionMutation.reset();
    cancelActionMutation.reset();
  }

  function startNewConversation() {
    setConversationId(null);
    setOptimisticMessage(null);
    setLocalContinuation(null);
    setQuestion("");
    resetMutationErrors();
  }

  function selectConversation(selectedConversationId: string) {
    if (isPending) return;
    setConversationId(selectedConversationId);
    setOptimisticMessage(null);
    setLocalContinuation(null);
    resetMutationErrors();
  }

  async function removeConversation(selectedConversationId: string) {
    if (isPending) {
      return;
    }

    deleteConversationMutation.reset();

    try {
      await deleteConversationMutation.mutateAsync(
        selectedConversationId,
      );

      if (conversationId === selectedConversationId) {
        startNewConversation();
      }
    } catch {
      // Mutation state renders the error in the workspace.
    }
  }

  function cancelClarification() {
    setLocalContinuation(null);
  }

  async function confirmPendingAction() {
    if (
      !pendingAction ||
      pendingAction.status !== "pending_confirmation" ||
      isPending
    ) {
      return;
    }

    confirmActionMutation.reset();

    try {
      await confirmActionMutation.mutateAsync(pendingAction.id);
      agentMutation.reset();
    } catch {
      // Mutation state renders the error in the workspace.
    }
  }

  async function cancelPendingAction() {
    if (
      !pendingAction ||
      pendingAction.status !== "pending_confirmation" ||
      isPending
    ) {
      return;
    }

    cancelActionMutation.reset();

    try {
      await cancelActionMutation.mutateAsync(pendingAction.id);
      agentMutation.reset();
    } catch {
      // Mutation state renders the error in the workspace.
    }
  }

  const requestError =
    agentMutation.error ??
    createConversationMutation.error ??
    deleteConversationMutation.error ??
    confirmActionMutation.error ??
    cancelActionMutation.error;

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Operational copilot"
        title="NovaScale AI"
        description="Investigate shipments, use indexed operational context, and prepare controlled write actions that always require explicit confirmation."
        actions={
          <div className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            Guardrails active
          </div>
        }
      />

      <div className="grid min-h-[680px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] lg:grid-cols-[19rem_minmax(0,1fr)]">
        <aside className="border-b border-slate-200 bg-slate-50/80 p-4 lg:border-b-0 lg:border-r">
          <button
            type="button"
            onClick={startNewConversation}
            disabled={isPending}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Icon name="plus" className="h-4 w-4" />
            New conversation
          </button>

          <div className="mt-6">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                Conversations
              </p>
              <span className="text-xs text-slate-400">
                {conversationsQuery.data?.length ?? 0}
              </span>
            </div>

            {conversationsQuery.isLoading ? (
              <p className="text-sm text-slate-500">Loading conversations...</p>
            ) : conversationsQuery.isError ? (
              <p className="text-sm text-rose-600">
                {conversationsQuery.error.message}
              </p>
            ) : conversationsQuery.data?.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 bg-white px-4 py-5 text-center">
                <Icon name="sparkles" className="mx-auto h-5 w-5 text-slate-400" />
                <p className="mt-2 text-xs leading-5 text-slate-500">
                  Saved conversations will appear here.
                </p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {conversationsQuery.data?.map((conversation) => {
                  const active = conversation.id === conversationId;
                  return (
                    <div
                      key={conversation.id}
                      className={`group rounded-xl border p-2.5 transition ${
                        active
                          ? "border-cyan-200 bg-cyan-50/70"
                          : "border-transparent hover:border-slate-200 hover:bg-white"
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => selectConversation(conversation.id)}
                        disabled={isPending}
                        className="block w-full truncate text-left text-sm font-medium text-slate-800 disabled:cursor-not-allowed"
                        title={conversation.title}
                      >
                        {conversation.title}
                      </button>
                      <div className="mt-1.5 flex items-center justify-between gap-2">
                        <span className="text-[11px] text-slate-400">Saved conversation</span>
                        <button
                          type="button"
                          onClick={() => void removeConversation(conversation.id)}
                          disabled={isPending}
                          className="text-[11px] font-medium text-slate-400 opacity-0 transition hover:text-rose-600 group-hover:opacity-100 disabled:cursor-not-allowed"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </aside>

        <section className="flex min-h-[680px] min-w-0 flex-col bg-white">
          <div className="border-b border-slate-100 px-5 py-4 sm:px-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-950 text-cyan-300">
                <Icon name="ai" className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  {conversationQuery.data?.title ?? "New operational conversation"}
                </p>
                <p className="text-xs text-slate-500">
                  Tenant-aware · permission-aware · confirmation required for writes
                </p>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto bg-slate-50/35 px-4 py-6 sm:px-6">
            {conversationQuery.isLoading && conversationId ? (
              <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">
                Loading conversation...
              </div>
            ) : null}

            {conversationQuery.isError && conversationId ? (
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                {conversationQuery.error.message}
              </div>
            ) : null}

            {messages.length === 0 &&
            !conversationQuery.isLoading &&
            !conversationQuery.isError ? (
              <WelcomePanel onPrompt={setQuestion} />
            ) : (
              <div className="mx-auto max-w-3xl space-y-5">
                {messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}
              </div>
            )}

            <div className="mx-auto mt-5 max-w-3xl space-y-4">
              {continuation?.kind === "shipment_selection" ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  <p className="font-semibold">Shipment clarification required</p>
                  <p className="mt-1 leading-6">
                    Provide a tracking number or shipment UUID to continue the request for <strong>{continuation.original_identifier}</strong>.
                  </p>
                </div>
              ) : null}

              {pendingAction ? (
                <div className="overflow-hidden rounded-2xl border border-amber-200 bg-white shadow-sm">
                  <div className="border-b border-amber-100 bg-amber-50 px-4 py-3.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-amber-900">
                        <Icon name="warning" className="h-4 w-4" />
                        <span className="text-sm font-semibold">Action requires confirmation</span>
                      </div>
                      <StatusBadge value={pendingAction.status} />
                    </div>
                  </div>
                  <div className="p-4">
                    <p className="text-sm font-semibold text-slate-900">{pendingAction.summary}</p>
                    <dl className="mt-4 grid gap-4 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
                      <ActionDetail label="Shipment" value={pendingAction.shipment_identifier} />
                      <ActionDetail label="Action state" value={pendingAction.status} />
                      {pendingAction.target_status ? (
                        <ActionDetail
                          label="Status transition"
                          value={`${pendingAction.expected_status} → ${pendingAction.target_status}`}
                        />
                      ) : null}
                      {pendingAction.new_notes ? (
                        <div className="sm:col-span-2">
                          <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Proposed notes</dt>
                          <dd className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{pendingAction.new_notes}</dd>
                        </div>
                      ) : null}
                    </dl>

                    {pendingAction.status === "pending_confirmation" ? (
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => void confirmPendingAction()}
                          disabled={isPending}
                          className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <Icon name="check" className="h-4 w-4" />
                          {confirmActionMutation.isPending ? "Executing..." : "Confirm action"}
                        </button>
                        <button
                          type="button"
                          onClick={() => void cancelPendingAction()}
                          disabled={isPending}
                          className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Cancel action
                        </button>
                      </div>
                    ) : null}

                    {pendingAction.status === "executing" ? (
                      <p className="mt-4 text-sm text-amber-700">
                        Execution is in progress. New messages remain blocked until the action resolves.
                      </p>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {agentMutation.isPending ? (
                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500 shadow-sm">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-500" />
                  NovaScale AI is analyzing the request...
                </div>
              ) : null}

              {requestError ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                  {requestError.message}
                </div>
              ) : null}
            </div>
          </div>

          <div className="border-t border-slate-200 bg-white p-4 sm:p-5">
            <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
              <div className="rounded-2xl border border-slate-300 bg-white p-2 shadow-[0_8px_30px_rgba(15,23,42,0.06)] focus-within:border-cyan-400 focus-within:ring-4 focus-within:ring-cyan-500/5">
                <textarea
                  id="question"
                  aria-label={pendingAction ? "Pending action" : continuation ? "Shipment identifier" : "Question"}
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  rows={3}
                  maxLength={4000}
                  disabled={Boolean(pendingAction)}
                  placeholder={
                    pendingAction
                      ? "Confirm or cancel the pending action before continuing..."
                      : continuation
                        ? "Enter the tracking number or shipment UUID..."
                        : "Ask about a shipment, investigate operations, or request a supported action..."
                  }
                  className="w-full resize-none border-0 bg-transparent px-3 py-2 text-sm leading-6 text-slate-900 outline-none placeholder:text-slate-400 focus:shadow-none disabled:cursor-not-allowed disabled:bg-slate-50"
                />
                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-2 pt-2">
                  <p className="text-[11px] text-slate-400">
                    AI output can be reviewed before any state-changing action.
                  </p>
                  <div className="flex items-center gap-2">
                    {continuation && !pendingAction ? (
                      <button
                        type="button"
                        onClick={cancelClarification}
                        disabled={isPending}
                        className="rounded-lg px-3 py-2 text-xs font-semibold text-slate-500 transition hover:bg-slate-50 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Cancel clarification
                      </button>
                    ) : null}
                    <button
                      type="submit"
                      disabled={isPending || Boolean(pendingAction) || !question.trim()}
                      className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {agentMutation.isPending ? "Thinking..." : continuation ? "Continue" : "Send"}
                      {!agentMutation.isPending ? <Icon name="arrow-right" className="h-4 w-4" /> : null}
                    </button>
                  </div>
                </div>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}

function WelcomePanel({ onPrompt }: { onPrompt: (prompt: string) => void }) {
  const prompts = [
    "Show me the current state of shipment SHIP-001",
    "Analyze a shipment for operational risk",
    "Summarize a shipment and its recent activity",
  ];

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center py-12 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-950 text-cyan-300 shadow-lg">
        <Icon name="sparkles" className="h-6 w-6" />
      </div>
      <h2 className="mt-5 text-xl font-semibold tracking-tight text-slate-950">
        Operational intelligence, in context
      </h2>
      <p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">
        Ask about shipment state, timeline context, operational issues, or supported actions. NovaScale keeps tenant and permission boundaries in the execution path.
      </p>
      <div className="mt-6 grid w-full gap-2 sm:grid-cols-3">
        {prompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onPrompt(prompt)}
            className="rounded-xl border border-slate-200 bg-white p-3 text-left text-xs leading-5 text-slate-600 transition hover:border-cyan-200 hover:bg-cyan-50/40 hover:text-slate-900"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: LocalMessage }) {
  const user = message.role === "user";
  return (
    <div className={`flex ${user ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[88%] sm:max-w-2xl ${user ? "rounded-2xl rounded-br-md bg-slate-950 px-4 py-3 text-white" : "rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 text-slate-700 shadow-sm"}`}>
        <div className={`mb-1.5 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] ${user ? "text-slate-400" : "text-cyan-700"}`}>
          {user ? "You" : "NovaScale AI"}
        </div>
        <div className="whitespace-pre-wrap text-sm leading-6">{message.content}</div>
      </div>
    </div>
  );
}

function ActionDetail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-slate-700">{value}</dd>
    </div>
  );
}

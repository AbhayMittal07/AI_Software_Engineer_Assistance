import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, MessageSquareCode, Plus, Send, Trash2, User } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/lib/api";
import type { ChatAnswer, ChatMessage, ChatSession, RepositoryDetail } from "@/lib/types";
import { Badge } from "@/components/common/Metrics";
import { EmptyState, InlineSpinner } from "@/components/common/States";
import { MarkdownView } from "@/components/common/MarkdownView";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function ChatPage() {
  const { repoId } = useParams();
  const queryClient = useQueryClient();
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const repoQuery = useQuery<RepositoryDetail>({
    queryKey: ["repository", repoId],
    queryFn: async () => (await api.get(`/repositories/${repoId}`)).data,
  });

  const suggestionsQuery = useQuery<string[]>({
    queryKey: ["chat-suggestions"],
    queryFn: async () => (await api.get("/chat/suggestions")).data,
    staleTime: Infinity,
  });

  const sessionsQuery = useQuery<ChatSession[]>({
    queryKey: ["chat-sessions", repoId],
    queryFn: async () => (await api.get(`/repositories/${repoId}/chat/sessions`)).data,
  });

  useEffect(() => {
    if (sessionId === null) {
      setMessages([]);
      return;
    }
    (async () => {
      try {
        const { data } = await api.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`);
        setMessages(data);
      } catch (error) {
        toast.error(apiError(error, "Could not load conversation"));
      }
    })();
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const ask = useMutation({
    mutationFn: async (question: string) =>
      (await api.post<ChatAnswer>(`/repositories/${repoId}/chat`, { message: question, session_id: sessionId })).data,
    onSuccess: (answer) => {
      setSessionId(answer.session_id);
      setMessages((prev) => [...prev, answer.answer]);
      void queryClient.invalidateQueries({ queryKey: ["chat-sessions", repoId] });
      if (!answer.ai_powered) toast.warning("AI provider unavailable — showing retrieved context only");
    },
    onError: (error) => {
      toast.error(apiError(error, "Chat request failed"));
      setMessages((prev) => prev.filter((message) => message.id !== -1));
    },
  });

  const removeSession = useMutation({
    mutationFn: async (id: number) => api.delete(`/chat/sessions/${id}`),
    onSuccess: (_, id) => {
      toast.success("Conversation deleted");
      if (id === sessionId) {
        setSessionId(null);
        setMessages([]);
      }
      void queryClient.invalidateQueries({ queryKey: ["chat-sessions", repoId] });
    },
    onError: (error) => toast.error(apiError(error)),
  });

  const send = (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || ask.isPending) return;
    setMessages((prev) => [
      ...prev,
      {
        id: -1,
        session_id: sessionId || 0,
        role: "user",
        content: trimmed,
        citations: [],
        created_at: new Date().toISOString(),
      },
    ]);
    setInput("");
    ask.mutate(trimmed);
  };

  const repo = repoQuery.data;

  return (
    <div className="space-y-6" data-testid="chat-page">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-6">
        <div>
          <p className="label-mono">
            <Link to={`/repositories/${repoId}`} className="text-primary underline underline-offset-4" data-testid="chat-repo-link">
              ← back to repository
            </Link>
          </p>
          <h1 className="mt-2 flex items-center gap-3 font-mono text-3xl font-extrabold uppercase tracking-tighter">
            <MessageSquareCode className="h-6 w-6 text-primary" /> Ask the codebase
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Retrieval-augmented answers grounded in {repo?.indexed_chunks ?? 0} indexed chunks from{" "}
            {repo?.name || "this repository"}.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setSessionId(null);
            setMessages([]);
          }}
          className="flex items-center gap-2 border border-border px-4 py-2 font-mono text-[11px] uppercase tracking-wider transition-colors hover:border-primary hover:text-primary"
          data-testid="new-conversation-button"
        >
          <Plus className="h-3.5 w-3.5" /> New conversation
        </button>
      </header>

      <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
        <aside className="panel h-fit" data-testid="chat-sessions-panel">
          <p className="label-mono border-b border-border px-4 py-3">Conversations</p>
          {sessionsQuery.data?.length ? (
            <ul>
              {sessionsQuery.data.map((session) => (
                <li key={session.id} className="flex items-center border-b border-border last:border-b-0">
                  <button
                    type="button"
                    onClick={() => setSessionId(session.id)}
                    className={cn(
                      "min-w-0 flex-1 border-l-2 px-4 py-3 text-left transition-colors",
                      sessionId === session.id ? "border-l-primary bg-primary/10" : "border-l-transparent hover:bg-muted/50"
                    )}
                    data-testid={`chat-session-${session.id}`}
                  >
                    <p className="truncate font-mono text-[11px]">{session.title}</p>
                    <p className="label-mono mt-0.5">
                      {session.message_count} msgs · {relativeTime(session.created_at)}
                    </p>
                  </button>
                  <button
                    type="button"
                    onClick={() => removeSession.mutate(session.id)}
                    className="px-3 text-muted-foreground transition-colors hover:text-signal-critical"
                    data-testid={`delete-session-${session.id}`}
                    aria-label="Delete conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-4 py-6 text-center font-mono text-[11px] text-muted-foreground">No conversations yet</p>
          )}
        </aside>

        <section className="panel flex min-h-[620px] flex-col" data-testid="chat-panel">
          <div className="flex-1 space-y-4 overflow-y-auto p-6" data-testid="chat-messages">
            {messages.length === 0 && (
              <div className="space-y-5">
                <EmptyState
                  title="Ask anything about this repository"
                  description="Answers cite the exact files retrieved from the vector index."
                  testId="chat-empty"
                />
                <div className="grid gap-2 sm:grid-cols-2">
                  {(suggestionsQuery.data || []).map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => send(suggestion)}
                      className="border border-border px-4 py-3 text-left font-mono text-[11px] transition-colors hover:border-primary hover:text-primary"
                      data-testid={`chat-suggestion-${suggestion.slice(0, 12).replace(/\s+/g, "-").toLowerCase()}`}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <article
                key={`${message.id}-${index}`}
                className={cn("flex gap-3", message.role === "user" ? "justify-end" : "justify-start")}
                data-testid={`chat-message-${message.role}-${index}`}
              >
                {message.role === "assistant" && (
                  <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center border border-primary text-primary">
                    <Bot className="h-3.5 w-3.5" />
                  </span>
                )}
                <div
                  className={cn(
                    "max-w-[85%] border p-4",
                    message.role === "user" ? "border-primary/40 bg-primary/10" : "border-border bg-card"
                  )}
                >
                  {message.role === "assistant" ? (
                    <MarkdownView content={message.content} testId={`chat-markdown-${index}`} />
                  ) : (
                    <p className="whitespace-pre-wrap font-mono text-xs">{message.content}</p>
                  )}
                  {message.citations?.length > 0 && (
                    <div className="mt-4 border-t border-border pt-3">
                      <p className="label-mono mb-2">Sources</p>
                      <div className="flex flex-wrap gap-2">
                        {message.citations.map((citation, citationIndex) => (
                          <Badge
                            key={`${citation.path}-${citationIndex}`}
                            className="border-border text-muted-foreground"
                            testId={`citation-${index}-${citationIndex}`}
                          >
                            {citation.path}
                            {citation.score != null ? ` · ${citation.score}` : ""}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                {message.role === "user" && (
                  <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center border border-border">
                    <User className="h-3.5 w-3.5" />
                  </span>
                )}
              </article>
            ))}

            {ask.isPending && (
              <div className="flex items-center gap-3" data-testid="chat-thinking">
                <span className="flex h-7 w-7 items-center justify-center border border-primary text-primary">
                  <Bot className="h-3.5 w-3.5" />
                </span>
                <InlineSpinner label="Retrieving context and reasoning…" />
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form
            onSubmit={(event) => {
              event.preventDefault();
              send(input);
            }}
            className="flex items-end gap-2 border-t border-border p-4"
            data-testid="chat-form"
          >
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  send(input);
                }
              }}
              rows={2}
              placeholder="Explain how authentication works…"
              className="flex-1 resize-none border border-border bg-background p-3 font-mono text-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
              data-testid="chat-input"
            />
            <button
              type="submit"
              disabled={!input.trim() || ask.isPending}
              className="flex h-12 items-center gap-2 border border-primary bg-primary px-5 font-mono text-[11px] uppercase tracking-wider text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-50"
              data-testid="chat-send-button"
            >
              <Send className="h-3.5 w-3.5" /> Send
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

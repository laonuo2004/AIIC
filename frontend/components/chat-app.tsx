"use client";

import {
  Bot,
  LogOut,
  Menu,
  MessageSquarePlus,
  PanelLeftClose,
  Send,
  UserRound,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  ConversationSummary,
  Message,
  User,
  getConversation,
  getMe,
  listConversations,
  login,
  logout,
  register,
  streamChat,
} from "@/lib/api";

type DraftMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type AuthMode = "login" | "register";

export function ChatApp() {
  const [user, setUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [booting, setBooting] = useState(true);

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<DraftMessage[]>([]);
  const [input, setInput] = useState("");
  const [chatError, setChatError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const transcriptRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    getMe()
      .then((currentUser) => {
        setUser(currentUser);
        return refreshConversations();
      })
      .catch(() => undefined)
      .finally(() => setBooting(false));
  }, []);

  useEffect(() => {
    transcriptRef.current?.scrollTo({
      top: transcriptRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const canSend = input.trim().length > 0 && !streaming;

  async function refreshConversations() {
    const items = await listConversations();
    setConversations(items);
    return items;
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError("");
    try {
      const nextUser =
        authMode === "register"
          ? await register(username.trim(), password)
          : await login(username.trim(), password);
      if (authMode === "register") {
        await login(username.trim(), password);
      }
      setUser(nextUser);
      setPassword("");
      await refreshConversations();
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed");
    }
  }

  async function selectConversation(id: number) {
    setChatError("");
    const detail = await getConversation(id);
    setActiveConversationId(detail.id);
    setMessages(
      detail.messages.map((message: Message) => ({
        id: String(message.id),
        role: message.role === "user" ? "user" : "assistant",
        content: message.content,
      })),
    );
  }

  function startNewConversation() {
    setActiveConversationId(null);
    setMessages([]);
    setChatError("");
    setInput("");
  }

  async function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = input.trim();
    if (!content || streaming) return;

    const assistantId = `assistant-${Date.now()}`;
    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: "user", content },
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setInput("");
    setChatError("");
    setStreaming(true);

    try {
      await streamChat(content, activeConversationId, (event) => {
        if (event.event === "meta") {
          setActiveConversationId(event.data.conversation_id);
          return;
        }

        if (event.event === "delta") {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, content: message.content + event.data.text }
                : message,
            ),
          );
          return;
        }

        if (event.event === "error") {
          setChatError(event.data.message);
          setMessages((current) => current.filter((message) => message.id !== assistantId));
          return;
        }

        if (event.event === "done") {
          refreshConversations().catch(() => undefined);
        }
      });
    } catch (error) {
      setMessages((current) => current.filter((message) => message.id !== assistantId));
      setChatError(error instanceof Error ? error.message : "Chat request failed");
    } finally {
      setStreaming(false);
    }
  }

  async function signOut() {
    await logout().catch(() => undefined);
    setUser(null);
    setConversations([]);
    startNewConversation();
  }

  const activeTitle = useMemo(() => {
    return conversations.find((item) => item.id === activeConversationId)?.title ?? "New thread";
  }, [activeConversationId, conversations]);

  if (booting) {
    return (
      <main className="boot-screen">
        <div className="boot-mark">AIIC</div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="auth-screen">
        <section className="auth-panel" aria-labelledby="auth-title">
          <div>
            <p className="eyebrow">Stack test prototype</p>
            <h1 id="auth-title">AIIC Chat</h1>
            <p className="auth-copy">
              FastAPI, SQLite sessions, LiteLLM streaming, and a reusable Next.js interface.
            </p>
          </div>

          <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
            <button
              className={authMode === "login" ? "active" : ""}
              type="button"
              onClick={() => setAuthMode("login")}
            >
              Login
            </button>
            <button
              className={authMode === "register" ? "active" : ""}
              type="button"
              onClick={() => setAuthMode("register")}
            >
              Register
            </button>
          </div>

          <form className="auth-form" onSubmit={submitAuth}>
            <label>
              Username
              <input
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                minLength={2}
              />
            </label>
            <label>
              Password
              <input
                autoComplete={authMode === "login" ? "current-password" : "new-password"}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={authMode === "register" ? 8 : 1}
              />
            </label>
            {authError ? <p className="form-error">{authError}</p> : null}
            <button className="primary-button" type="submit">
              {authMode === "login" ? "Login" : "Create account"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className={sidebarOpen ? "sidebar open" : "sidebar"}>
        <div className="sidebar-head">
          <button className="icon-button desktop-only" onClick={() => setSidebarOpen(false)} type="button">
            <PanelLeftClose size={18} />
          </button>
          <span>Threads</span>
          <button className="icon-button" onClick={startNewConversation} type="button" title="New chat">
            <MessageSquarePlus size={18} />
          </button>
        </div>
        <div className="conversation-list">
          {conversations.map((conversation) => (
            <button
              className={conversation.id === activeConversationId ? "conversation active" : "conversation"}
              key={conversation.id}
              onClick={() => selectConversation(conversation.id)}
              type="button"
            >
              <span>{conversation.title}</span>
              <small>{new Date(conversation.updated_at).toLocaleDateString()}</small>
            </button>
          ))}
          {conversations.length === 0 ? <p className="empty-note">No saved threads yet.</p> : null}
        </div>
      </aside>

      <section className="chat-panel">
        <header className="chat-header">
          <button className="icon-button mobile-toggle" onClick={() => setSidebarOpen(true)} type="button">
            <Menu size={18} />
          </button>
          <div>
            <p>{activeTitle}</p>
            <span>Signed in as {user.username}</span>
          </div>
          <button className="icon-button" onClick={signOut} type="button" title="Logout">
            <LogOut size={18} />
          </button>
        </header>

        <div className="transcript" ref={transcriptRef}>
          {messages.length === 0 ? (
            <div className="starter">
              <Bot size={28} />
              <h2>Start with a focused stack-test prompt.</h2>
              <p>Ask for a product idea, an implementation outline, or a quick API sanity check.</p>
            </div>
          ) : (
            messages.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
                <div className="avatar">{message.role === "user" ? <UserRound size={16} /> : <Bot size={16} />}</div>
                <p>{message.content || (streaming ? "Thinking..." : "")}</p>
              </article>
            ))
          )}
        </div>

        {chatError ? <div className="chat-error">{chatError}</div> : null}

        <form className="composer" onSubmit={submitMessage}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Send a message through the FastAPI + LiteLLM backend"
            rows={1}
          />
          <button className="send-button" disabled={!canSend} type="submit" title="Send">
            <Send size={18} />
          </button>
        </form>
      </section>
    </main>
  );
}

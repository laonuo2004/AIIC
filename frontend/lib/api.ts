export type User = {
  id: number;
  username: string;
};

export type ConversationSummary = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
};

export type Message = {
  id: number;
  role: "user" | "assistant" | string;
  content: string;
  created_at: string;
};

export type ConversationDetail = ConversationSummary & {
  messages: Message[];
};

export type StreamEvent =
  | { event: "meta"; data: { conversation_id: number } }
  | { event: "delta"; data: { text: string } }
  | { event: "error"; data: { message: string } }
  | { event: "done"; data: { conversation_id: number } };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    const detail = typeof body.detail === "string" ? body.detail : "Request failed";
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function getMe() {
  return request<User>("/api/auth/me");
}

export function login(username: string, password: string) {
  return request<User>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function register(username: string, password: string) {
  return request<User>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout() {
  return request<void>("/api/auth/logout", { method: "POST" });
}

export async function listConversations() {
  const result = await request<{ conversations: ConversationSummary[] }>("/api/conversations");
  return result.conversations;
}

export function getConversation(id: number) {
  return request<ConversationDetail>(`/api/conversations/${id}`);
}

export async function streamChat(
  message: string,
  conversationId: number | null,
  onEvent: (event: StreamEvent) => void,
) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => ({ detail: "Chat request failed" }));
    throw new Error(typeof body.detail === "string" ? body.detail : "Chat request failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const parsed = parseSseBlock(block);
      if (parsed) onEvent(parsed);
    }
  }
}

function parseSseBlock(block: string): StreamEvent | null {
  const eventLine = block.split("\n").find((line) => line.startsWith("event: "));
  const dataLine = block.split("\n").find((line) => line.startsWith("data: "));
  if (!eventLine || !dataLine) return null;

  const event = eventLine.replace("event: ", "") as StreamEvent["event"];
  const data = JSON.parse(dataLine.replace("data: ", ""));

  if (event === "meta" || event === "delta" || event === "error" || event === "done") {
    return { event, data } as StreamEvent;
  }

  return null;
}

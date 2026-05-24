export type User = {
  id: number;
  username: string;
};

export type Attachment = {
  id: number;
  name: string;
  mime: string;
  size: number;
  kind: "text" | "image" | "pdf" | string;
  created_at: string;
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
  attachments?: Attachment[];
};

export type ConversationDetail = ConversationSummary & {
  messages: Message[];
};

export type OpenRouterConfig = {
  configured: boolean;
  key_hint: string | null;
  selected_model_id: string | null;
  enabled_model_ids: string[];
  last_synced_at: string | null;
};

export type OpenRouterModel = {
  id: string;
  name: string;
  input_modalities: string[];
  output_modalities: string[];
  context_length: number | null;
  pricing: Record<string, string | number | null> | null;
};

export type RuntimeStatus = {
  status?: string;
  app_env?: string;
  database?: string;
  upload_limit_bytes?: number;
  max_attachments_per_message?: number;
  proxy_enabled?: boolean;
  default_model?: string;
  model_strategy?: {
    deep?: string;
    fast?: string;
    feedback?: string;
  };
  max_pdf_pages_per_attachment?: number;
  [key: string]: unknown;
};

export type CandidateProfile = {
  self_introduction: string;
  project_experience: string;
  target_direction: string;
  weak_points: string;
};

export type InterviewTurn = {
  id: number;
  turn_index: number;
  question: string;
  answer: string | null;
  feedback: {
    strengths?: string[];
    weaknesses?: string[];
    score?: number;
    advice?: string;
    [key: string]: unknown;
  } | null;
  model_used: string | null;
  created_at: string;
  answered_at: string | null;
};

export type Interview = {
  id: number;
  title: string;
  status: "active" | "finished" | string;
  profile: CandidateProfile & Record<string, unknown>;
  target_direction: string;
  interview_type: string;
  weak_points: string;
  current_question: string | null;
  final_report: {
    overall_score?: number;
    summary?: string;
    strengths?: string[];
    weaknesses?: string[];
    next_steps?: string[];
    [key: string]: unknown;
  } | null;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
  turns: InterviewTurn[];
  attachments: Attachment[];
};

export type InterviewSummary = {
  id: number;
  title: string;
  status: string;
  target_direction: string;
  current_question: string | null;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
};

export type FaceAsset = {
  id: number;
  status: string;
  image_url: string;
  audio_url: string;
  speaker_id: string | null;
  ready_video_url: string | null;
  listening_video_url: string | null;
  latest_speaking_video_url: string | null;
  provider_status: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type FaceSession = {
  id: number;
  asset_id: number;
  status: string;
  created_at: string;
};

export type FaceServerEvent =
  | { event: "session_started"; speaker_id?: string; resource_id?: string }
  | { event: "asr_partial"; text: string }
  | { event: "asr_final"; text: string }
  | { event: "assistant_text"; text: string }
  | { event: "assistant_audio"; audio: string; mime?: string }
  | { event: "tts_started" }
  | { event: "tts_ended" }
  | { event: "speaking_video_pending" }
  | { event: "speaking_video_ready"; video_url: string }
  | { event: "session_finished" }
  | { event: "error"; message: string };

export type StreamEvent =
  | { event: "meta"; data: { conversation_id: number; model_id?: string | null } }
  | { event: "delta"; data: { text: string } }
  | { event: "error"; data: { message: string } }
  | { event: "done"; data: { conversation_id: number; model_id?: string | null } };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function errorMessageFromBody(body: unknown, fallback: string) {
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return fallback;
  }
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== "object") return "";
        const record = item as { loc?: unknown; msg?: unknown };
        const field = Array.isArray(record.loc) ? record.loc.slice(1).join(".") : "";
        const message = typeof record.msg === "string" ? record.msg : "";
        return [field, message].filter(Boolean).join(": ");
      })
      .filter(Boolean);
    if (messages.length > 0) {
      return messages.join("; ");
    }
  }
  return fallback;
}

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
    throw new Error(errorMessageFromBody(body, "Request failed"));
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

export function getOpenRouterConfig() {
  return request<OpenRouterConfig>("/api/providers/openrouter/config");
}

export function saveOpenRouterKey(apiKey: string) {
  return request<OpenRouterConfig>("/api/providers/openrouter/key", {
    method: "PUT",
    body: JSON.stringify({ api_key: apiKey }),
  });
}

export function deleteOpenRouterKey() {
  return request<void>("/api/providers/openrouter/key", { method: "DELETE" });
}

export async function listOpenRouterModels(refresh = false) {
  return request<{ models: OpenRouterModel[]; warning?: string }>(
    `/api/providers/openrouter/models?refresh=${refresh ? "true" : "false"}`,
  );
}

export function updateOpenRouterModels(enabledModelIds: string[], selectedModelId: string | null) {
  return request<OpenRouterConfig>("/api/providers/openrouter/models", {
    method: "PATCH",
    body: JSON.stringify({
      enabled_model_ids: enabledModelIds,
      selected_model_id: selectedModelId,
    }),
  });
}

export async function uploadAttachments(files: File[]) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));

  const response = await fetch(`${API_BASE}/api/attachments`, {
    method: "POST",
    credentials: "include",
    body: form,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Upload failed" }));
    const detail = typeof body.detail === "string" ? body.detail : "Upload failed";
    throw new Error(detail);
  }

  return response.json() as Promise<{ attachments: Attachment[] }>;
}

export async function createFaceAsset(image: File, audio: File) {
  const form = new FormData();
  form.append("image", image);
  form.append("audio", audio);

  const response = await fetch(`${API_BASE}/api/face/assets`, {
    method: "POST",
    credentials: "include",
    body: form,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Face asset upload failed" }));
    throw new Error(errorMessageFromBody(body, "Face asset upload failed"));
  }

  return response.json() as Promise<FaceAsset>;
}

export function cloneFaceVoice(assetId: number) {
  return request<FaceAsset>(`/api/face/assets/${assetId}/voice-clone`, { method: "POST" });
}

export function generateFaceVideos(assetId: number) {
  return request<FaceAsset>(`/api/face/assets/${assetId}/videos`, { method: "POST" });
}

export function getFaceAsset(assetId: number) {
  return request<FaceAsset>(`/api/face/assets/${assetId}`);
}

export function createFaceSession(assetId: number) {
  return request<FaceSession>("/api/face/session", {
    method: "POST",
    body: JSON.stringify({ asset_id: assetId }),
  });
}

export function faceWebSocketUrl(sessionId: number) {
  const base = API_BASE || window.location.origin;
  const url = new URL(`/api/face/session/${sessionId}/stream`, base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function attachmentUrl(id: number) {
  return `${API_BASE}/api/attachments/${id}`;
}

export async function getRuntimeStatus() {
  const candidates = ["/api/status", "/health"];
  for (const path of candidates) {
    try {
      return await request<RuntimeStatus>(path);
    } catch {
      // The Settings page is intentionally best-effort while backend status endpoints evolve.
    }
  }
  return null;
}

export async function listInterviews() {
  const result = await request<{ interviews: InterviewSummary[] }>("/api/interviews");
  return result.interviews;
}

export function createInterview(profile: CandidateProfile, attachmentIds: number[] = []) {
  return request<Interview>("/api/interviews", {
    method: "POST",
    body: JSON.stringify({ ...profile, interview_type: "text", attachment_ids: attachmentIds }),
  });
}

export function getInterview(id: number) {
  return request<Interview>(`/api/interviews/${id}`);
}

export function submitInterviewAnswer(id: number, answer: string) {
  return request<Interview>(`/api/interviews/${id}/answers`, {
    method: "POST",
    body: JSON.stringify({ answer }),
  });
}

export function finishInterview(id: number) {
  return request<Interview>(`/api/interviews/${id}/finish`, { method: "POST" });
}

export async function streamChat(
  message: string,
  conversationId: number | null,
  modelId: string | null,
  attachmentIds: number[],
  onEvent: (event: StreamEvent) => void,
) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      model_id: modelId,
      attachment_ids: attachmentIds,
    }),
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

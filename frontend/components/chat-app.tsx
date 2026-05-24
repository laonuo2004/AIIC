"use client";

import {
  Bot,
  Check,
  FileText,
  Image as ImageIcon,
  KeyRound,
  Loader2,
  LogOut,
  Menu,
  MessageSquare,
  MessageSquarePlus,
  Moon,
  PanelLeftClose,
  Paperclip,
  RefreshCw,
  Send,
  Settings,
  Sun,
  Trash2,
  UserRound,
} from "lucide-react";
import {
  ChangeEvent,
  FormEvent,
  KeyboardEvent,
  ReactNode,
  RefObject,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  Attachment,
  ConversationSummary,
  Message,
  OpenRouterConfig,
  OpenRouterModel,
  RuntimeStatus,
  User,
  attachmentUrl,
  deleteOpenRouterKey,
  getConversation,
  getMe,
  getOpenRouterConfig,
  getRuntimeStatus,
  listConversations,
  listOpenRouterModels,
  login,
  logout,
  register,
  saveOpenRouterKey,
  streamChat,
  updateOpenRouterModels,
  uploadAttachments,
} from "@/lib/api";

type DraftMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  attachments: Attachment[];
};

type AuthMode = "login" | "register";
type View = "chat" | "openrouter" | "settings";
type ThemeMode = "system" | "light" | "dark";

const THEME_KEY = "aiic-theme-mode";
const MAX_ATTACHMENTS = 4;

export function ChatApp() {
  const [user, setUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [booting, setBooting] = useState(true);

  const [view, setView] = useState<View>("chat");
  const [themeMode, setThemeMode] = useState<ThemeMode>("system");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<DraftMessage[]>([]);
  const [input, setInput] = useState("");
  const [pendingAttachments, setPendingAttachments] = useState<Attachment[]>([]);
  const [chatError, setChatError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [conversationPanelOpen, setConversationPanelOpen] = useState(true);

  const [providerConfig, setProviderConfig] = useState<OpenRouterConfig | null>(null);
  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [providerError, setProviderError] = useState("");
  const [providerNotice, setProviderNotice] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [syncingModels, setSyncingModels] = useState(false);

  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [settingsError, setSettingsError] = useState("");

  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const saved = window.localStorage.getItem(THEME_KEY) as ThemeMode | null;
    if (saved === "system" || saved === "light" || saved === "dark") {
      setThemeMode(saved);
    }
    setConversationPanelOpen(window.matchMedia("(min-width: 860px)").matches);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.themeMode = themeMode;
    window.localStorage.setItem(THEME_KEY, themeMode);
  }, [themeMode]);

  useEffect(() => {
    getMe()
      .then(async (currentUser) => {
        setUser(currentUser);
        await Promise.all([refreshConversations(), refreshProvider(false), refreshStatus()]);
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

  const selectedModelId = providerConfig?.selected_model_id ?? null;
  const enabledModelIds = useMemo(
    () => providerConfig?.enabled_model_ids ?? [],
    [providerConfig?.enabled_model_ids],
  );
  const activeTitle = useMemo(
    () => conversations.find((item) => item.id === activeConversationId)?.title ?? "New thread",
    [activeConversationId, conversations],
  );
  const enabledModels = useMemo(
    () => models.filter((model) => enabledModelIds.includes(model.id)),
    [enabledModelIds, models],
  );
  const canSend =
    !streaming && !uploading && (input.trim().length > 0 || pendingAttachments.length > 0);

  async function refreshConversations() {
    const items = await listConversations();
    setConversations(items);
    return items;
  }

  async function refreshProvider(refreshModels: boolean) {
    const [config, modelResponse] = await Promise.all([
      getOpenRouterConfig(),
      listOpenRouterModels(refreshModels).catch(() => ({ models: [] as OpenRouterModel[] })),
    ]);
    setProviderConfig(config);
    setModels(modelResponse.models);
    if ("warning" in modelResponse && modelResponse.warning) {
      setProviderNotice(modelResponse.warning);
    }
  }

  async function refreshStatus() {
    try {
      const status = await getRuntimeStatus();
      setRuntimeStatus(status);
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "Runtime status unavailable");
    }
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError("");
    try {
      const trimmedUsername = username.trim();
      const nextUser =
        authMode === "register"
          ? await register(trimmedUsername, password)
          : await login(trimmedUsername, password);
      if (authMode === "register") {
        await login(trimmedUsername, password);
      }
      setUser(nextUser);
      setPassword("");
      await Promise.all([refreshConversations(), refreshProvider(false), refreshStatus()]);
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
        attachments: message.attachments ?? [],
      })),
    );
    if (window.matchMedia("(max-width: 859px)").matches) {
      setConversationPanelOpen(false);
    }
  }

  function startNewConversation() {
    setActiveConversationId(null);
    setMessages([]);
    setChatError("");
    setInput("");
    setPendingAttachments([]);
    setView("chat");
  }

  async function submitMessage(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const content = input.trim();
    if (!canSend) return;
    if (!selectedModelId) {
      setChatError("Select an enabled OpenRouter model before sending.");
      setView("openrouter");
      return;
    }

    const attachments = pendingAttachments;
    const assistantId = `assistant-${Date.now()}`;
    setMessages((current) => [
      ...current,
      {
        id: `user-${Date.now()}`,
        role: "user",
        content: content || "(attachments)",
        attachments,
      },
      { id: assistantId, role: "assistant", content: "", attachments: [] },
    ]);
    setInput("");
    setPendingAttachments([]);
    setChatError("");
    setStreaming(true);

    try {
      await streamChat(
        content || "Please analyze the attached files.",
        activeConversationId,
        selectedModelId,
        attachments.map((item) => item.id),
        (event) => {
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
        },
      );
    } catch (error) {
      setMessages((current) => current.filter((message) => message.id !== assistantId));
      setChatError(error instanceof Error ? error.message : "Chat request failed");
    } finally {
      setStreaming(false);
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      submitMessage();
    }
  }

  async function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length === 0) return;
    if (pendingAttachments.length + files.length > MAX_ATTACHMENTS) {
      setChatError(`Attach up to ${MAX_ATTACHMENTS} files per message.`);
      return;
    }
    setUploading(true);
    setChatError("");
    try {
      const result = await uploadAttachments(files);
      setPendingAttachments((current) => [...current, ...result.attachments]);
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function saveProviderKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingKey(true);
    setProviderError("");
    setProviderNotice("");
    try {
      const config = await saveOpenRouterKey(apiKey.trim());
      setProviderConfig(config);
      setApiKey("");
      const response = await listOpenRouterModels(false);
      setModels(response.models);
      setProviderNotice("Key verified and model cache refreshed.");
    } catch (error) {
      setProviderError(error instanceof Error ? error.message : "Could not save key");
    } finally {
      setSavingKey(false);
    }
  }

  async function syncModels() {
    setSyncingModels(true);
    setProviderError("");
    setProviderNotice("");
    try {
      const response = await listOpenRouterModels(true);
      const config = await getOpenRouterConfig();
      setModels(response.models);
      setProviderConfig(config);
      setProviderNotice(response.warning ?? "Model list refreshed.");
    } catch (error) {
      setProviderError(error instanceof Error ? error.message : "Could not refresh models");
    } finally {
      setSyncingModels(false);
    }
  }

  async function toggleModel(modelId: string) {
    if (!providerConfig) return;
    const enabled = new Set(providerConfig.enabled_model_ids);
    if (enabled.has(modelId)) {
      enabled.delete(modelId);
    } else {
      enabled.add(modelId);
    }
    const nextEnabled = Array.from(enabled);
    const selected =
      providerConfig.selected_model_id && nextEnabled.includes(providerConfig.selected_model_id)
        ? providerConfig.selected_model_id
        : nextEnabled[0] ?? null;
    const nextConfig = await updateOpenRouterModels(nextEnabled, selected);
    setProviderConfig(nextConfig);
  }

  async function chooseModel(modelId: string) {
    if (!providerConfig) return;
    const enabled = providerConfig.enabled_model_ids.includes(modelId)
      ? providerConfig.enabled_model_ids
      : [...providerConfig.enabled_model_ids, modelId];
    const nextConfig = await updateOpenRouterModels(enabled, modelId);
    setProviderConfig(nextConfig);
  }

  async function removeKey() {
    await deleteOpenRouterKey();
    setProviderConfig({
      configured: false,
      key_hint: null,
      selected_model_id: null,
      enabled_model_ids: [],
      last_synced_at: null,
    });
    setProviderNotice("OpenRouter key and model preferences removed.");
  }

  async function signOut() {
    await logout().catch(() => undefined);
    setUser(null);
    setProviderConfig(null);
    setModels([]);
    setConversations([]);
    startNewConversation();
  }

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
            <p className="eyebrow">Chat Studio</p>
            <h1 id="auth-title">AIIC</h1>
            <p className="auth-copy">
              A compact multi-provider chat workspace with encrypted OpenRouter settings,
              persistence, and file-aware context.
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
    <main className="studio-shell">
      <aside className="rail" aria-label="Primary navigation">
        <button className="rail-logo" type="button" onClick={() => setView("chat")}>
          AI
        </button>
        <nav className="rail-nav">
          <RailButton active={view === "chat"} label="Chat" onClick={() => setView("chat")}>
            <MessageSquare size={19} />
          </RailButton>
          <RailButton
            active={view === "openrouter"}
            label="OpenRouter"
            onClick={() => setView("openrouter")}
          >
            <KeyRound size={19} />
          </RailButton>
          <RailButton
            active={view === "settings"}
            label="Settings"
            onClick={() => setView("settings")}
          >
            <Settings size={19} />
          </RailButton>
        </nav>
        <button className="rail-action" onClick={signOut} type="button" title="Logout">
          <LogOut size={19} />
        </button>
      </aside>

      {view === "chat" ? (
        <aside className={conversationPanelOpen ? "thread-panel open" : "thread-panel"}>
          <div className="thread-head">
            <button
              className="icon-button"
              onClick={() => setConversationPanelOpen(false)}
              type="button"
              title="Collapse threads"
            >
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
                className={
                  conversation.id === activeConversationId ? "conversation active" : "conversation"
                }
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
      ) : null}

      <section className="workspace">
        {view === "chat" ? (
          <ChatWorkspace
            activeTitle={activeTitle}
            chatError={chatError}
            conversationPanelOpen={conversationPanelOpen}
            enabledModels={enabledModels}
            fileInputRef={fileInputRef}
            handleComposerKeyDown={handleComposerKeyDown}
            handleFiles={handleFiles}
            input={input}
            messages={messages}
            onOpenThreads={() => setConversationPanelOpen(true)}
            pendingAttachments={pendingAttachments}
            removePendingAttachment={(id) =>
              setPendingAttachments((current) => current.filter((item) => item.id !== id))
            }
            selectedModelId={selectedModelId}
            setInput={setInput}
            streaming={streaming}
            submitMessage={submitMessage}
            transcriptRef={transcriptRef}
            uploading={uploading}
            user={user}
            canSend={canSend}
          />
        ) : null}

        {view === "openrouter" ? (
          <OpenRouterWorkspace
            apiKey={apiKey}
            chooseModel={chooseModel}
            config={providerConfig}
            models={models}
            providerError={providerError}
            providerNotice={providerNotice}
            removeKey={removeKey}
            saveProviderKey={saveProviderKey}
            savingKey={savingKey}
            setApiKey={setApiKey}
            syncModels={syncModels}
            syncingModels={syncingModels}
            toggleModel={toggleModel}
          />
        ) : null}

        {view === "settings" ? (
          <SettingsWorkspace
            refreshStatus={refreshStatus}
            runtimeStatus={runtimeStatus}
            settingsError={settingsError}
            setThemeMode={setThemeMode}
            themeMode={themeMode}
          />
        ) : null}
      </section>
    </main>
  );
}

function RailButton({
  active,
  children,
  label,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={active ? "rail-action active" : "rail-action"} onClick={onClick} type="button" title={label}>
      {children}
      <span>{label}</span>
    </button>
  );
}

function ChatWorkspace(props: {
  activeTitle: string;
  canSend: boolean;
  chatError: string;
  conversationPanelOpen: boolean;
  enabledModels: OpenRouterModel[];
  fileInputRef: RefObject<HTMLInputElement | null>;
  handleComposerKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  handleFiles: (event: ChangeEvent<HTMLInputElement>) => void;
  input: string;
  messages: DraftMessage[];
  onOpenThreads: () => void;
  pendingAttachments: Attachment[];
  removePendingAttachment: (id: number) => void;
  selectedModelId: string | null;
  setInput: (value: string) => void;
  streaming: boolean;
  submitMessage: (event?: FormEvent<HTMLFormElement>) => void;
  transcriptRef: RefObject<HTMLDivElement | null>;
  uploading: boolean;
  user: User;
}) {
  const selectedModel = props.enabledModels.find((model) => model.id === props.selectedModelId);

  return (
    <div className="chat-workspace">
      <header className="workspace-header">
        <button
          className={props.conversationPanelOpen ? "icon-button mobile-only" : "icon-button"}
          onClick={props.onOpenThreads}
          type="button"
          title="Open threads"
        >
          <Menu size={18} />
        </button>
        <div>
          <p>{props.activeTitle}</p>
          <span>
            {props.user.username} · {selectedModel?.name ?? props.selectedModelId ?? "No model selected"}
          </span>
        </div>
      </header>

      <div className="transcript" ref={props.transcriptRef}>
        {props.messages.length === 0 ? (
          <div className="starter">
            <Bot size={30} />
            <h2>Build context, then ask.</h2>
            <p>Choose an OpenRouter model, attach text or images, and stream the response into a saved thread.</p>
          </div>
        ) : (
          props.messages.map((message) => <MessageBubble key={message.id} message={message} streaming={props.streaming} />)
        )}
      </div>

      {props.chatError ? <div className="chat-error">{props.chatError}</div> : null}

      <form className="composer" onSubmit={props.submitMessage}>
        {props.pendingAttachments.length > 0 ? (
          <div className="attachment-strip">
            {props.pendingAttachments.map((attachment) => (
              <AttachmentChip
                attachment={attachment}
                key={attachment.id}
                onRemove={() => props.removePendingAttachment(attachment.id)}
              />
            ))}
          </div>
        ) : null}
        <textarea
          value={props.input}
          onChange={(event) => props.setInput(event.target.value)}
          onKeyDown={props.handleComposerKeyDown}
          placeholder="Enter for newline, Ctrl+Enter to send"
          rows={3}
        />
        <div className="composer-actions">
          <input
            accept=".txt,.md,.json,.csv,.log,image/png,image/jpeg,image/webp,image/gif"
            className="hidden-input"
            multiple
            onChange={props.handleFiles}
            ref={props.fileInputRef}
            type="file"
          />
          <button
            className="icon-button"
            disabled={props.uploading || props.pendingAttachments.length >= MAX_ATTACHMENTS}
            onClick={() => props.fileInputRef.current?.click()}
            type="button"
            title="Attach files"
          >
            {props.uploading ? <Loader2 className="spin" size={18} /> : <Paperclip size={18} />}
          </button>
          <button className="send-button" disabled={!props.canSend} type="submit" title="Send">
            {props.streaming ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
          </button>
        </div>
      </form>
    </div>
  );
}

function MessageBubble({ message, streaming }: { message: DraftMessage; streaming: boolean }) {
  return (
    <article className={`message ${message.role}`}>
      <div className="avatar">{message.role === "user" ? <UserRound size={16} /> : <Bot size={16} />}</div>
      <div className="message-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content || (streaming && message.role === "assistant" ? "Thinking..." : "")}
        </ReactMarkdown>
        {message.attachments.length > 0 ? (
          <div className="message-attachments">
            {message.attachments.map((attachment) => (
              <a href={attachmentUrl(attachment.id)} key={attachment.id} target="_blank" rel="noreferrer">
                {attachment.kind === "image" ? <ImageIcon size={14} /> : <FileText size={14} />}
                {attachment.name}
              </a>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function AttachmentChip({
  attachment,
  onRemove,
}: {
  attachment: Attachment;
  onRemove: () => void;
}) {
  return (
    <span className="attachment-chip">
      {attachment.kind === "image" ? <ImageIcon size={14} /> : <FileText size={14} />}
      {attachment.name}
      <button onClick={onRemove} type="button" title="Remove attachment">
        <Trash2 size={13} />
      </button>
    </span>
  );
}

function OpenRouterWorkspace(props: {
  apiKey: string;
  chooseModel: (modelId: string) => void;
  config: OpenRouterConfig | null;
  models: OpenRouterModel[];
  providerError: string;
  providerNotice: string;
  removeKey: () => void;
  saveProviderKey: (event: FormEvent<HTMLFormElement>) => void;
  savingKey: boolean;
  setApiKey: (value: string) => void;
  syncModels: () => void;
  syncingModels: boolean;
  toggleModel: (modelId: string) => void;
}) {
  return (
    <div className="page-view">
      <header className="page-header">
        <div>
          <p className="eyebrow">Provider</p>
          <h1>OpenRouter</h1>
        </div>
        <button className="secondary-button" onClick={props.syncModels} type="button" disabled={props.syncingModels}>
          {props.syncingModels ? <Loader2 className="spin" size={17} /> : <RefreshCw size={17} />}
          Sync models
        </button>
      </header>

      <section className="settings-grid">
        <div className="panel">
          <h2>API key</h2>
          <p className="muted">
            Stored encrypted on the backend. After save, only the last four characters are shown.
          </p>
          <form className="key-form" onSubmit={props.saveProviderKey}>
            <input
              autoComplete="off"
              placeholder="sk-or-v1-..."
              type="password"
              value={props.apiKey}
              onChange={(event) => props.setApiKey(event.target.value)}
            />
            <button className="primary-button" disabled={props.savingKey || props.apiKey.trim().length < 8} type="submit">
              {props.savingKey ? "Verifying..." : "Save key"}
            </button>
          </form>
          <div className="status-row">
            <span className={props.config?.configured ? "status-dot ok" : "status-dot"} />
            {props.config?.configured ? `Configured · ****${props.config.key_hint}` : "Not configured"}
          </div>
          {props.config?.configured ? (
            <button className="danger-button" onClick={props.removeKey} type="button">
              Delete key
            </button>
          ) : null}
        </div>

        <div className="panel">
          <h2>Model selection</h2>
          <p className="muted">
            Enable models for this account, then choose the default used by Chat.
          </p>
          {props.providerError ? <p className="form-error">{props.providerError}</p> : null}
          {props.providerNotice ? <p className="notice">{props.providerNotice}</p> : null}
          <div className="model-list">
            {props.models.map((model) => {
              const enabled = props.config?.enabled_model_ids.includes(model.id) ?? false;
              const selected = props.config?.selected_model_id === model.id;
              return (
                <div className={selected ? "model-row selected" : "model-row"} key={model.id}>
                  <label>
                    <input checked={enabled} type="checkbox" onChange={() => props.toggleModel(model.id)} />
                    <span>
                      <strong>{model.name}</strong>
                      <small>
                        {model.id} · {model.input_modalities.join(", ") || "text"} ·{" "}
                        {model.context_length ? `${model.context_length.toLocaleString()} ctx` : "ctx unknown"}
                      </small>
                    </span>
                  </label>
                  <button
                    className="icon-button"
                    disabled={!enabled}
                    onClick={() => props.chooseModel(model.id)}
                    type="button"
                    title="Use as default"
                  >
                    <Check size={16} />
                  </button>
                </div>
              );
            })}
            {props.models.length === 0 ? <p className="empty-note light">Save a key, then sync models.</p> : null}
          </div>
        </div>
      </section>
    </div>
  );
}

function SettingsWorkspace(props: {
  refreshStatus: () => void;
  runtimeStatus: RuntimeStatus | null;
  settingsError: string;
  setThemeMode: (mode: ThemeMode) => void;
  themeMode: ThemeMode;
}) {
  return (
    <div className="page-view">
      <header className="page-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>Settings</h1>
        </div>
        <button className="secondary-button" onClick={props.refreshStatus} type="button">
          <RefreshCw size={17} />
          Refresh
        </button>
      </header>

      <section className="settings-grid">
        <div className="panel">
          <h2>Theme</h2>
          <div className="segmented" role="radiogroup" aria-label="Theme mode">
            <ThemeButton active={props.themeMode === "system"} onClick={() => props.setThemeMode("system")}>
              <Settings size={15} />
              System
            </ThemeButton>
            <ThemeButton active={props.themeMode === "light"} onClick={() => props.setThemeMode("light")}>
              <Sun size={15} />
              Light
            </ThemeButton>
            <ThemeButton active={props.themeMode === "dark"} onClick={() => props.setThemeMode("dark")}>
              <Moon size={15} />
              Dark
            </ThemeButton>
          </div>
        </div>

        <div className="panel">
          <h2>Runtime</h2>
          {props.settingsError ? <p className="form-error">{props.settingsError}</p> : null}
          <dl className="status-table">
            <StatusItem label="Environment" value={props.runtimeStatus?.app_env ?? "unknown"} />
            <StatusItem label="Database" value={props.runtimeStatus?.database ?? "unknown"} />
            <StatusItem
              label="Upload limit"
              value={formatBytes(props.runtimeStatus?.upload_limit_bytes)}
            />
            <StatusItem
              label="Attachments/message"
              value={String(props.runtimeStatus?.max_attachments_per_message ?? "unknown")}
            />
            <StatusItem
              label="Proxy env"
              value={props.runtimeStatus?.proxy_enabled ? "enabled" : "not detected"}
            />
            <StatusItem label="Default model" value={props.runtimeStatus?.default_model ?? "unknown"} />
          </dl>
        </div>
      </section>
    </div>
  );
}

function ThemeButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button className={active ? "active" : ""} onClick={onClick} type="button">
      {children}
    </button>
  );
}

function StatusItem({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  );
}

function formatBytes(value?: number) {
  if (!value) return "unknown";
  if (value >= 1024 * 1024) return `${Math.round(value / 1024 / 1024)}MB`;
  return `${Math.round(value / 1024)}KB`;
}

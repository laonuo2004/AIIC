"use client";

import {
  Bot,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  CircleAlert,
  FileAudio,
  FileText,
  ImagePlus,
  Loader2,
  LogOut,
  MessageSquareText,
  Mic,
  Moon,
  PlayCircle,
  RefreshCw,
  Send,
  Settings,
  Sparkles,
  Square,
  Sun,
  Trash2,
  UserRound,
  Video,
  Volume2,
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";

import {
  CandidateProfile,
  Attachment,
  FaceAsset,
  FaceServerEvent,
  FaceSession,
  Interview,
  InterviewSummary,
  RuntimeStatus,
  User,
  cloneFaceVoice,
  createFaceAsset,
  createFaceSession,
  createInterview,
  faceWebSocketUrl,
  finishInterview,
  generateFaceVideos,
  getInterview,
  getMe,
  getRuntimeStatus,
  listInterviews,
  login,
  logout,
  register,
  submitInterviewAnswer,
  uploadAttachments,
} from "@/lib/api";

type AuthMode = "login" | "register";
type View = "text" | "face" | "settings";
type ThemeMode = "system" | "light" | "dark";

const THEME_KEY = "researchmocker-theme-mode";

const EMPTY_PROFILE: CandidateProfile = {
  self_introduction: "",
  project_experience: "",
  target_direction: "",
  weak_points: "",
};

export function ChatApp() {
  const [user, setUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [booting, setBooting] = useState(true);

  const [view, setView] = useState<View>("text");
  const [themeMode, setThemeMode] = useState<ThemeMode>("system");
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [settingsError, setSettingsError] = useState("");

  const [profile, setProfile] = useState<CandidateProfile>(EMPTY_PROFILE);
  const [profileAttachments, setProfileAttachments] = useState<Attachment[]>([]);
  const [uploadError, setUploadError] = useState("");
  const [interviews, setInterviews] = useState<InterviewSummary[]>([]);
  const [activeInterview, setActiveInterview] = useState<Interview | null>(null);
  const [answer, setAnswer] = useState("");
  const [interviewError, setInterviewError] = useState("");
  const [working, setWorking] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(THEME_KEY) as ThemeMode | null;
    if (saved === "system" || saved === "light" || saved === "dark") {
      setThemeMode(saved);
    }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.themeMode = themeMode;
    window.localStorage.setItem(THEME_KEY, themeMode);
  }, [themeMode]);

  useEffect(() => {
    getMe()
      .then(async (currentUser) => {
        setUser(currentUser);
        await Promise.all([refreshInterviews(), refreshStatus()]);
      })
      .catch(() => undefined)
      .finally(() => setBooting(false));
  }, []);

  const activeTurn = useMemo(
    () => activeInterview?.turns.find((turn) => turn.answer === null) ?? null,
    [activeInterview],
  );

  const answeredTurns = useMemo(
    () => activeInterview?.turns.filter((turn) => turn.answer !== null) ?? [],
    [activeInterview],
  );

  const canStart =
    profile.self_introduction.trim().length > 0 &&
    profile.project_experience.trim().length > 0 &&
    profile.target_direction.trim().length > 0;

  async function refreshInterviews() {
    const items = await listInterviews();
    setInterviews(items);
    return items;
  }

  async function refreshStatus() {
    try {
      const status = await getRuntimeStatus();
      setRuntimeStatus(status);
      setSettingsError("");
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
      await Promise.all([refreshInterviews(), refreshStatus()]);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed");
    }
  }

  async function startInterview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canStart || working) return;
    setWorking(true);
    setInterviewError("");
    try {
      const created = await createInterview({
        self_introduction: profile.self_introduction.trim(),
        project_experience: profile.project_experience.trim(),
        target_direction: profile.target_direction.trim(),
        weak_points: profile.weak_points.trim(),
      }, profileAttachments.map((attachment) => attachment.id));
      setActiveInterview(created);
      await refreshInterviews();
    } catch (error) {
      setInterviewError(error instanceof Error ? error.message : "Could not start interview");
    } finally {
      setWorking(false);
    }
  }

  async function selectInterview(id: number) {
    setWorking(true);
    setInterviewError("");
    try {
      setActiveInterview(await getInterview(id));
    } catch (error) {
      setInterviewError(error instanceof Error ? error.message : "Could not load interview");
    } finally {
      setWorking(false);
    }
  }

  async function submitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeInterview || !answer.trim() || working) return;
    setWorking(true);
    setInterviewError("");
    try {
      setActiveInterview(await submitInterviewAnswer(activeInterview.id, answer.trim()));
      setAnswer("");
      await refreshInterviews();
    } catch (error) {
      setInterviewError(error instanceof Error ? error.message : "Could not submit answer");
    } finally {
      setWorking(false);
    }
  }

  async function finishActiveInterview() {
    if (!activeInterview || working) return;
    setWorking(true);
    setInterviewError("");
    try {
      setActiveInterview(await finishInterview(activeInterview.id));
      await refreshInterviews();
    } catch (error) {
      setInterviewError(error instanceof Error ? error.message : "Could not finish interview");
    } finally {
      setWorking(false);
    }
  }

  function resetInterviewDraft() {
    setActiveInterview(null);
    setAnswer("");
    setInterviewError("");
  }

  async function addProfileAttachments(files: File[]) {
    if (files.length === 0 || working) return;
    setWorking(true);
    setUploadError("");
    try {
      const result = await uploadAttachments(files);
      setProfileAttachments((current) => [...current, ...result.attachments]);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setWorking(false);
    }
  }

  function removeProfileAttachment(id: number) {
    setProfileAttachments((current) => current.filter((attachment) => attachment.id !== id));
  }

  async function signOut() {
    await logout().catch(() => undefined);
    setUser(null);
    setInterviews([]);
    setActiveInterview(null);
    setPassword("");
  }

  if (booting) {
    return (
      <main className="boot-screen">
        <div className="boot-mark">ResearchMocker</div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="auth-screen">
        <section className="auth-panel" aria-labelledby="auth-title">
          <p className="eyebrow">Research interview practice</p>
          <h1 id="auth-title">ResearchMocker</h1>
          <p className="auth-copy">
            Practice project deep-dive pressure drills with adaptive teacher-style questions,
            risk-point feedback, and a final review report.
          </p>

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
      <aside className="rail" aria-label="Primary navigation">
        <button className="rail-logo" type="button" onClick={() => setView("text")}>
          RM
        </button>
        <nav className="rail-nav">
          <RailButton active={view === "text"} label="Text Interview" onClick={() => setView("text")}>
            <MessageSquareText size={19} />
          </RailButton>
          <RailButton
            active={view === "face"}
            label="Face-to-Face"
            onClick={() => setView("face")}
          >
            <Video size={19} />
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
          <span>Logout</span>
        </button>
      </aside>

      <section className="workspace">
        {view === "text" ? (
          <TextInterviewWorkspace
            activeInterview={activeInterview}
            activeTurn={activeTurn}
            answer={answer}
            answeredTurns={answeredTurns}
            canStart={canStart}
            error={interviewError}
            finishActiveInterview={finishActiveInterview}
            interviews={interviews}
            profile={profile}
            profileAttachments={profileAttachments}
            resetInterviewDraft={resetInterviewDraft}
            removeProfileAttachment={removeProfileAttachment}
            selectInterview={selectInterview}
            addProfileAttachments={addProfileAttachments}
            setAnswer={setAnswer}
            setProfile={setProfile}
            startInterview={startInterview}
            submitAnswer={submitAnswer}
            uploadError={uploadError}
            user={user}
            working={working}
          />
        ) : null}

        {view === "face" ? <FaceWorkspace /> : null}

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

function TextInterviewWorkspace(props: {
  activeInterview: Interview | null;
  activeTurn: Interview["turns"][number] | null;
  answer: string;
  answeredTurns: Interview["turns"];
  canStart: boolean;
  error: string;
  finishActiveInterview: () => void;
  interviews: InterviewSummary[];
  profile: CandidateProfile;
  profileAttachments: Attachment[];
  resetInterviewDraft: () => void;
  removeProfileAttachment: (id: number) => void;
  selectInterview: (id: number) => void;
  addProfileAttachments: (files: File[]) => void;
  setAnswer: (value: string) => void;
  setProfile: (value: CandidateProfile) => void;
  startInterview: (event: FormEvent<HTMLFormElement>) => void;
  submitAnswer: (event: FormEvent<HTMLFormElement>) => void;
  uploadError: string;
  user: User;
  working: boolean;
}) {
  return (
    <div className="interview-layout">
      <aside className="session-panel">
        <div>
          <p className="eyebrow">Text Interview</p>
          <h2>Saved sessions</h2>
        </div>
        <button className="secondary-button" onClick={props.resetInterviewDraft} type="button">
          New practice
        </button>
        <div className="session-list">
          {props.interviews.map((interview) => (
            <button
              className={
                props.activeInterview?.id === interview.id ? "session-row active" : "session-row"
              }
              key={interview.id}
              onClick={() => props.selectInterview(interview.id)}
              type="button"
            >
              <strong>{interview.title}</strong>
              <span>{interview.status} · {new Date(interview.updated_at).toLocaleDateString()}</span>
            </button>
          ))}
          {props.interviews.length === 0 ? (
            <p className="empty-note">No interviews yet. Start with the candidate profile.</p>
          ) : null}
        </div>
      </aside>

      <div className="interview-main">
        <header className="workspace-header">
          <div>
            <p>{props.activeInterview?.title ?? "ResearchMocker"}</p>
            <span>{props.user.username} · project deep dive practice</span>
          </div>
          {props.activeInterview && props.activeInterview.status !== "finished" ? (
            <button className="secondary-button" onClick={props.finishActiveInterview} type="button" disabled={props.working}>
              {props.working ? <Loader2 className="spin" size={16} /> : <CheckCircle2 size={16} />}
              Finish
            </button>
          ) : null}
        </header>

        {props.error ? <div className="chat-error">{props.error}</div> : null}

        {!props.activeInterview ? (
          <ProfileForm
            canStart={props.canStart}
            profile={props.profile}
            profileAttachments={props.profileAttachments}
            removeProfileAttachment={props.removeProfileAttachment}
            addProfileAttachments={props.addProfileAttachments}
            setProfile={props.setProfile}
            startInterview={props.startInterview}
            uploadError={props.uploadError}
            working={props.working}
          />
        ) : (
          <InterviewRoom
            activeInterview={props.activeInterview}
            activeTurn={props.activeTurn}
            answer={props.answer}
            answeredTurns={props.answeredTurns}
            setAnswer={props.setAnswer}
            submitAnswer={props.submitAnswer}
            working={props.working}
          />
        )}
      </div>
    </div>
  );
}

function ProfileForm(props: {
  canStart: boolean;
  profile: CandidateProfile;
  profileAttachments: Attachment[];
  removeProfileAttachment: (id: number) => void;
  addProfileAttachments: (files: File[]) => void;
  setProfile: (value: CandidateProfile) => void;
  startInterview: (event: FormEvent<HTMLFormElement>) => void;
  uploadError: string;
  working: boolean;
}) {
  function update(key: keyof CandidateProfile, value: string) {
    props.setProfile({ ...props.profile, [key]: value });
  }

  return (
    <form className="profile-form" onSubmit={props.startInterview}>
      <div className="page-header compact">
        <div>
          <p className="eyebrow">Candidate profile</p>
          <h1>Start a focused mock interview</h1>
          <p className="muted">
            You will enter 2-3 rounds of project deep dive practice focused on details,
            personal contribution, and experiment evidence.
          </p>
        </div>
      </div>

      <label>
        Self-introduction
        <textarea
          value={props.profile.self_introduction}
          onChange={(event) => update("self_introduction", event.target.value)}
          placeholder="CS/AI background, current year, research interests..."
          rows={4}
          required
        />
      </label>
      <label>
        Project or research experience
        <textarea
          value={props.profile.project_experience}
          onChange={(event) => update("project_experience", event.target.value)}
          placeholder="Problem, method, your contribution, results, and evaluation..."
          rows={6}
          required
        />
      </label>
      <div className="form-grid">
        <label>
          Target direction
          <input
            value={props.profile.target_direction}
            onChange={(event) => update("target_direction", event.target.value)}
            placeholder="Research internship, lab admission, graduate interview..."
            required
          />
        </label>
        <label>
          Weak points
          <input
            value={props.profile.weak_points}
            onChange={(event) => update("weak_points", event.target.value)}
            placeholder="Metrics, motivation, technical depth..."
          />
        </label>
      </div>
      <section className="attachment-dropzone" aria-label="Candidate materials">
        <label className="file-picker">
          <FileText size={18} />
          <span>
            Add notes, diagrams, or PDF pages
            <small>TXT, MD, JSON, CSV, PNG, JPEG, WebP, GIF, PDF</small>
          </span>
          <input
            type="file"
            multiple
            accept=".txt,.md,.json,.csv,.log,image/png,image/jpeg,image/webp,image/gif,application/pdf,.pdf"
            onChange={(event) => {
              props.addProfileAttachments(Array.from(event.target.files ?? []));
              event.currentTarget.value = "";
            }}
            disabled={props.working}
          />
        </label>
        {props.uploadError ? <p className="form-error">{props.uploadError}</p> : null}
        {props.profileAttachments.length > 0 ? (
          <div className="attachment-chip-list">
            {props.profileAttachments.map((attachment) => (
              <div className="attachment-chip" key={attachment.id}>
                <FileText size={15} />
                <span>
                  <strong>{attachment.name}</strong>
                  <small>{attachment.kind.toUpperCase()} · {formatBytes(attachment.size)}</small>
                </span>
                <button
                  type="button"
                  title="Remove attachment"
                  onClick={() => props.removeProfileAttachment(attachment.id)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        ) : null}
      </section>
      <button className="primary-button wide" type="submit" disabled={!props.canStart || props.working}>
        {props.working ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
        Start interview
      </button>
    </form>
  );
}

function InterviewRoom(props: {
  activeInterview: Interview;
  activeTurn: Interview["turns"][number] | null;
  answer: string;
  answeredTurns: Interview["turns"];
  setAnswer: (value: string) => void;
  submitAnswer: (event: FormEvent<HTMLFormElement>) => void;
  working: boolean;
}) {
  const [visibleTurnIndex, setVisibleTurnIndex] = useState(0);
  const visibleTurn = props.answeredTurns[visibleTurnIndex] ?? null;

  useEffect(() => {
    setVisibleTurnIndex((current) => Math.min(current, Math.max(props.answeredTurns.length - 1, 0)));
  }, [props.answeredTurns.length]);

  return (
    <div className="interview-room">
      <section className="question-panel">
        <div className="interviewer-mark">
          <Bot size={22} />
        </div>
        <div>
          <p className="eyebrow">Current question</p>
          <h2>{props.activeTurn?.question ?? "Interview complete"}</h2>
        </div>
      </section>

      {props.activeInterview.status !== "finished" && props.activeTurn ? (
        <form className="answer-form" onSubmit={props.submitAnswer}>
          <textarea
            value={props.answer}
            onChange={(event) => props.setAnswer(event.target.value)}
            placeholder="Answer as you would in an interview. Include your role, method, evidence, and tradeoffs."
            rows={6}
          />
          <button className="send-button text" disabled={!props.answer.trim() || props.working} type="submit">
            {props.working ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
            Submit answer
          </button>
        </form>
      ) : null}

      {props.activeInterview.final_report ? (
        <ReportCard report={props.activeInterview.final_report} />
      ) : null}

      {visibleTurn ? (
        <section className="qa-review-panel" aria-label="Answered questions">
          <div className="qa-review-header">
            <div>
              <p className="eyebrow">Answered Q&A</p>
              <h3>Question {visibleTurn.turn_index} of {props.answeredTurns.length}</h3>
            </div>
            <div className="pager-controls">
              <button
                type="button"
                title="Previous answer"
                disabled={visibleTurnIndex === 0}
                onClick={() => setVisibleTurnIndex((current) => Math.max(current - 1, 0))}
              >
                <ChevronLeft size={17} />
              </button>
              <button
                type="button"
                title="Next answer"
                disabled={visibleTurnIndex >= props.answeredTurns.length - 1}
                onClick={() =>
                  setVisibleTurnIndex((current) =>
                    Math.min(current + 1, props.answeredTurns.length - 1),
                  )
                }
              >
                <ChevronRight size={17} />
              </button>
            </div>
          </div>
          <article className="qa-review-body">
            <div className="qa-copy">
              <div className="turn-question">
                <UserRound size={17} />
                <strong>{visibleTurn.question}</strong>
              </div>
              <p className="answer-text">{visibleTurn.answer}</p>
            </div>
            {visibleTurn.feedback ? <FeedbackCard feedback={visibleTurn.feedback} /> : null}
          </article>
        </section>
      ) : null}
    </div>
  );
}

function FeedbackCard({ feedback }: { feedback: NonNullable<Interview["turns"][number]["feedback"]> }) {
  return (
    <div className="feedback-card">
      <div className="score-row">
        <div className="score-pill">{feedback.score ?? "?"}/10</div>
      </div>
      <div className="feedback-comparison">
        <ListBlock title="Strengths" items={feedback.strengths ?? []} />
        <ListBlock title="Risk points" items={feedback.weaknesses ?? []} />
      </div>
      {feedback.advice ? (
        <div className="advice-row">
          <h3>Rewrite direction</h3>
          <p>{feedback.advice}</p>
        </div>
      ) : null}
    </div>
  );
}

function ReportCard({ report }: { report: NonNullable<Interview["final_report"]> }) {
  return (
    <section className="report-card">
      <div>
        <p className="eyebrow">Final report</p>
        <h2>{report.overall_score ?? "?"}/10 overall</h2>
        <p>{report.summary}</p>
      </div>
      <ListBlock title="Strengths" items={report.strengths ?? []} />
      <ListBlock title="Vulnerable follow-up points" items={report.weaknesses ?? []} />
      <ListBlock title="24-hour practice plan" items={report.next_steps ?? []} />
    </section>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="list-block">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

type FaceStage =
  | "setup"
  | "preparing_voice"
  | "generating_videos"
  | "ready"
  | "listening"
  | "speaking"
  | "error";

function FaceWorkspace() {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [asset, setAsset] = useState<FaceAsset | null>(null);
  const [session, setSession] = useState<FaceSession | null>(null);
  const [stage, setStage] = useState<FaceStage>("setup");
  const [statusLines, setStatusLines] = useState<string[]>(["Upload image and audio to start."]);
  const [transcript, setTranscript] = useState("");
  const [assistantText, setAssistantText] = useState("");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const canPrepare = Boolean(imageFile && audioFile && !working);
  const visualUrl =
    stage === "speaking" && asset?.latest_speaking_video_url
      ? asset.latest_speaking_video_url
      : asset?.ready_video_url || asset?.image_url || "";

  useEffect(() => {
    return () => {
      socketRef.current?.close();
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  function pushStatus(line: string) {
    setStatusLines((current) => [line, ...current].slice(0, 5));
  }

  async function prepareAsset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!imageFile || !audioFile || working) return;
    setWorking(true);
    setError("");
    setTranscript("");
    setAssistantText("");
    try {
      setStage("preparing_voice");
      pushStatus("Uploading face assets.");
      const uploaded = await createFaceAsset(imageFile, audioFile);
      setAsset(uploaded);
      pushStatus("Registering cloned voice from reference audio.");
      const voiceReady = await cloneFaceVoice(uploaded.id);
      setAsset(voiceReady);
      setStage("generating_videos");
      pushStatus("Submitting optional OmniHuman video jobs.");
      let videoReady = voiceReady;
      try {
        videoReady = await generateFaceVideos(uploaded.id);
        setAsset(videoReady);
        pushStatus("Video jobs submitted. Speech remains the realtime path.");
      } catch (videoError) {
        const message =
          videoError instanceof Error ? videoError.message : "Video generation is not configured.";
        setAsset((current) => (current ? { ...current, error_message: message } : current));
        pushStatus(`Video setup skipped: ${message}`);
      }
      const createdSession = await createFaceSession(videoReady.id);
      setSession(createdSession);
      setStage("ready");
      pushStatus("Realtime speech session is ready.");
    } catch (prepareError) {
      setStage("error");
      setError(prepareError instanceof Error ? prepareError.message : "Could not prepare face interview.");
    } finally {
      setWorking(false);
    }
  }

  function ensureSocket() {
    if (!session) throw new Error("Prepare a face session first.");
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      return socketRef.current;
    }
    const socket = new WebSocket(faceWebSocketUrl(session.id));
    socketRef.current = socket;
    socket.onopen = () => socket.send(JSON.stringify({ event: "start_session" }));
    socket.onmessage = (message) => handleServerEvent(JSON.parse(message.data) as FaceServerEvent);
    socket.onerror = () => {
      setStage("error");
      setError("Realtime speech connection failed.");
    };
    socket.onclose = () => {
      if (stage !== "error") pushStatus("Realtime connection closed.");
    };
    return socket;
  }

  function handleServerEvent(event: FaceServerEvent) {
    if (event.event === "session_started") {
      pushStatus("Provider session started.");
      return;
    }
    if (event.event === "asr_partial" || event.event === "asr_final") {
      setTranscript(event.text);
      return;
    }
    if (event.event === "assistant_text") {
      setAssistantText(event.text);
      setStage("speaking");
      return;
    }
    if (event.event === "assistant_audio") {
      playAssistantAudio(event.audio, event.mime ?? "audio/wav");
      setStage("speaking");
      return;
    }
    if (event.event === "speaking_video_ready") {
      setAsset((current) =>
        current ? { ...current, latest_speaking_video_url: event.video_url } : current,
      );
      return;
    }
    if (event.event === "tts_ended" || event.event === "session_finished") {
      setStage("ready");
      return;
    }
    if (event.event === "error") {
      setStage("error");
      setError(event.message);
    }
  }

  function playAssistantAudio(base64: string, mime: string) {
    const audio = new Audio(`data:${mime};base64,${base64}`);
    audio.onended = () => setStage("ready");
    void audio.play().catch(() => pushStatus("Assistant audio is ready but browser autoplay blocked it."));
  }

  async function startListening() {
    if (!session || working || stage === "listening") return;
    setError("");
    try {
      const socket = ensureSocket();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = async (event) => {
        if (event.data.size === 0 || socket.readyState !== WebSocket.OPEN) return;
        socket.send(JSON.stringify({ event: "audio_chunk", audio: await blobToBase64(event.data) }));
      };
      recorder.start(500);
      setStage("listening");
      pushStatus("Listening. Release stop when your answer is complete.");
    } catch (listenError) {
      setStage("error");
      setError(
        listenError instanceof Error
          ? listenError.message
          : "Microphone access failed. Browser HTTPS rules may block HTTP demos.",
      );
    }
  }

  function stopListening() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    socketRef.current?.send(JSON.stringify({ event: "end_asr" }));
    setStage("ready");
    pushStatus("Answer audio sent.");
  }

  return (
    <div className="page-view">
      <header className="page-header">
        <div>
          <p className="eyebrow">Experimental</p>
          <h1>Face-to-Face Interview</h1>
          <p className="muted">
            Push-to-talk realtime speech with optional OmniHuman video enhancement. Text Interview
            remains the stable MVP path.
          </p>
        </div>
      </header>
      <section className="face-grid">
        <form className="panel face-setup" onSubmit={prepareAsset}>
          <h2>Setup</h2>
          <label className="file-drop">
            <ImagePlus size={22} />
            <span>{imageFile ? imageFile.name : "Interviewer image"}</span>
            <input
              accept="image/png,image/jpeg,image/webp"
              type="file"
              onChange={(event) => setImageFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <label className="file-drop">
            <FileAudio size={22} />
            <span>{audioFile ? audioFile.name : "Reference audio"}</span>
            <input
              accept="audio/mpeg,audio/wav,audio/mp4,audio/ogg,audio/aac"
              type="file"
              onChange={(event) => setAudioFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <button className="primary-button" disabled={!canPrepare} type="submit">
            {working ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />}
            Prepare interviewer
          </button>
          {error ? <p className="form-error">{error}</p> : null}
        </form>

        <section className="panel face-stage-panel">
          <div className={`face-visual face-${stage}`}>
            {visualUrl ? (
              visualUrl.endsWith(".mp4") || visualUrl.includes(".mp4?") ? (
                <video autoPlay loop muted playsInline src={visualUrl} />
              ) : (
                // eslint-disable-next-line @next/next/no-img-element
                <img alt="Digital interviewer" src={visualUrl} />
              )
            ) : (
              <Video size={54} />
            )}
          </div>
          <div className="face-controls">
            <StatusPill stage={stage} />
            {stage === "listening" ? (
              <button className="danger-button" onClick={stopListening} type="button">
                <Square size={17} />
                Stop
              </button>
            ) : (
              <button
                className="primary-button"
                disabled={!session || working}
                onClick={startListening}
                type="button"
              >
                <Mic size={17} />
                Push to talk
              </button>
            )}
          </div>
          <div className="face-transcript-grid">
            <div>
              <h3>Candidate</h3>
              <p>{transcript || "Microphone transcript will appear here."}</p>
            </div>
            <div>
              <h3>Interviewer</h3>
              <p>{assistantText || "Realtime response text will appear here."}</p>
            </div>
          </div>
        </section>

        <section className="state-strip face-status-strip">
          {statusLines.map((line) => (
            <span key={line}>{line}</span>
          ))}
        </section>
        <section className="panel face-provider-panel">
          <h2>Provider state</h2>
          <dl className="status-table">
            <dt>Asset</dt>
            <dd>{asset ? `#${asset.id} ${asset.status}` : "Not prepared"}</dd>
            <dt>Voice</dt>
            <dd>{asset?.speaker_id ? "Cloned voice registered" : "Waiting"}</dd>
            <dt>Video</dt>
            <dd>{asset?.error_message || asset?.provider_status || "Optional"}</dd>
            <dt>Session</dt>
            <dd>{session ? `#${session.id} ${session.status}` : "Not started"}</dd>
          </dl>
        </section>
      </section>
    </div>
  );
}

function StatusPill({ stage }: { stage: FaceStage }) {
  const icon =
    stage === "listening" ? <Mic size={16} /> : stage === "speaking" ? <Volume2 size={16} /> : stage === "error" ? <CircleAlert size={16} /> : <PlayCircle size={16} />;
  return (
    <span className={`status-pill face-status-${stage}`}>
      {icon}
      {stage.replace("_", " ")}
    </span>
  );
}

function blobToBase64(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
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
            <StatusItem label="Upload limit" value={formatBytes(props.runtimeStatus?.upload_limit_bytes)} />
            <StatusItem
              label="Attachments/message"
              value={String(props.runtimeStatus?.max_attachments_per_message ?? "unknown")}
            />
            <StatusItem label="Proxy env" value={props.runtimeStatus?.proxy_enabled ? "enabled" : "not detected"} />
            <StatusItem label="Deep model" value={props.runtimeStatus?.model_strategy?.deep ?? "configured server-side"} />
            <StatusItem label="Fast model" value={props.runtimeStatus?.model_strategy?.fast ?? "configured server-side"} />
            <StatusItem label="Feedback model" value={props.runtimeStatus?.model_strategy?.feedback ?? "configured server-side"} />
            <StatusItem
              label="PDF page limit"
              value={String(props.runtimeStatus?.max_pdf_pages_per_attachment ?? "unknown")}
            />
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

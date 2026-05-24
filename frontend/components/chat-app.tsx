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
  pollFaceVideos,
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
          <p className="eyebrow">保研科研面试</p>
          <h1 id="auth-title">ResearchMocker</h1>
          <p className="auth-copy">
            帮你练项目追问：发现回答漏洞、补齐证据、讲清个人贡献。
          </p>

          <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
            <button
              className={authMode === "login" ? "active" : ""}
              type="button"
              onClick={() => setAuthMode("login")}
            >
              登录
            </button>
            <button
              className={authMode === "register" ? "active" : ""}
              type="button"
              onClick={() => setAuthMode("register")}
            >
              注册
            </button>
          </div>

          <form className="auth-form" onSubmit={submitAuth}>
            <label>
              用户名
              <input
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                minLength={2}
              />
            </label>
            <label>
              密码
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
              {authMode === "login" ? "登录" : "创建账号"}
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
          <RailButton active={view === "text"} label="模拟面试" onClick={() => setView("text")}>
            <MessageSquareText size={19} />
          </RailButton>
          <RailButton
            active={view === "face"}
            label="数字人面试"
            onClick={() => setView("face")}
          >
            <Video size={19} />
          </RailButton>
          <RailButton
            active={view === "settings"}
            label="设置"
            onClick={() => setView("settings")}
          >
            <Settings size={19} />
          </RailButton>
        </nav>
        <button className="rail-action" onClick={signOut} type="button" title="退出登录">
          <LogOut size={19} />
          <span>退出</span>
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
          <p className="eyebrow">模拟面试</p>
          <h2>练习记录</h2>
        </div>
        <button className="secondary-button" onClick={props.resetInterviewDraft} type="button">
          新建练习
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
            <p className="empty-note">还没有练习记录。先填写面试资料。</p>
          ) : null}
        </div>
      </aside>

      <div className="interview-main">
        <header className="workspace-header">
          <div>
            <p>{props.activeInterview?.title ?? "ResearchMocker"}</p>
            <span>{props.user.username} · 项目追问练习</span>
          </div>
          {props.activeInterview && props.activeInterview.status !== "finished" ? (
            <button className="secondary-button" onClick={props.finishActiveInterview} type="button" disabled={props.working}>
              {props.working ? <Loader2 className="spin" size={16} /> : <CheckCircle2 size={16} />}
              结束
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
          <p className="eyebrow">面试资料</p>
          <h1>开始项目模拟面试</h1>
          <p className="muted">
            接下来会连续追问 2-3 轮，重点看实现细节、个人贡献和实验依据。
          </p>
        </div>
      </div>

      <label>
        自我介绍
        <textarea
          value={props.profile.self_introduction}
          onChange={(event) => update("self_introduction", event.target.value)}
          placeholder="学校年级、专业背景、研究方向和代表经历..."
          rows={4}
          required
        />
      </label>
      <label>
        项目经历
        <textarea
          value={props.profile.project_experience}
          onChange={(event) => update("project_experience", event.target.value)}
          placeholder="问题、方法、你的贡献、实验结果和评价指标..."
          rows={6}
          required
        />
      </label>
      <div className="form-grid">
        <label>
          面试方向
          <input
            value={props.profile.target_direction}
            onChange={(event) => update("target_direction", event.target.value)}
            placeholder="保研面试、实验室面试、科研实习..."
            required
          />
        </label>
        <label>
          最担心的问题
          <input
            value={props.profile.weak_points}
            onChange={(event) => update("weak_points", event.target.value)}
            placeholder="指标、动机、技术细节、个人贡献..."
          />
        </label>
      </div>
      <section className="attachment-dropzone" aria-label="Candidate materials">
        <label className="file-picker">
          <FileText size={18} />
          <span>
            上传项目材料
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
                  title="移除附件"
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
        开始面试
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
  const previousInterviewId = useRef(props.activeInterview.id);
  const previousAnsweredLength = useRef(props.answeredTurns.length);
  const visibleTurn = props.answeredTurns[visibleTurnIndex] ?? null;

  useEffect(() => {
    const latestIndex = Math.max(props.answeredTurns.length - 1, 0);
    const interviewChanged = previousInterviewId.current !== props.activeInterview.id;
    const answeredLengthIncreased = props.answeredTurns.length > previousAnsweredLength.current;

    setVisibleTurnIndex((current) =>
      interviewChanged || answeredLengthIncreased ? latestIndex : Math.min(current, latestIndex),
    );
    previousInterviewId.current = props.activeInterview.id;
    previousAnsweredLength.current = props.answeredTurns.length;
  }, [props.activeInterview.id, props.answeredTurns.length]);

  return (
    <div className="interview-room">
      <section className="question-panel">
        <div className="interviewer-mark">
          <Bot size={22} />
        </div>
        <div>
          <p className="eyebrow">当前问题</p>
          <h2>{props.activeTurn?.question ?? "面试已完成"}</h2>
        </div>
      </section>

      {props.activeInterview.status !== "finished" && props.activeTurn ? (
        <form className="answer-form" onSubmit={props.submitAnswer}>
          <textarea
            value={props.answer}
            onChange={(event) => props.setAnswer(event.target.value)}
            placeholder="请像真实面试一样用中文回答，说明你的角色、方法、证据和取舍。"
            rows={6}
          />
          <button className="send-button text" disabled={!props.answer.trim() || props.working} type="submit">
            {props.working ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
            提交回答
          </button>
        </form>
      ) : null}

      {props.activeInterview.final_report ? (
        <ReportCard report={props.activeInterview.final_report} />
      ) : null}

      {visibleTurn ? (
        <section className="qa-review-panel" aria-label="已回答问题">
          <div className="qa-review-header">
            <div>
              <p className="eyebrow">回答复盘</p>
              <h3>第 {visibleTurn.turn_index} 题 / 共 {props.answeredTurns.length} 题</h3>
            </div>
            <div className="pager-controls">
              <button
                type="button"
                title="上一题"
                disabled={visibleTurnIndex === 0}
                onClick={() => setVisibleTurnIndex((current) => Math.max(current - 1, 0))}
              >
                <ChevronLeft size={17} />
              </button>
              <button
                type="button"
                title="下一题"
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
        <ListBlock title="回答亮点" items={feedback.strengths ?? []} />
        <ListBlock title="容易被追问的地方" items={feedback.weaknesses ?? []} />
      </div>
      {feedback.advice ? (
        <div className="advice-row">
          <h3>下次怎么答</h3>
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
        <p className="eyebrow">最终报告</p>
        <h2>总分 {report.overall_score ?? "?"}/10</h2>
        <p>{report.summary}</p>
      </div>
      <ListBlock title="优势" items={report.strengths ?? []} />
      <ListBlock title="最容易卡住的问题" items={report.weaknesses ?? []} />
      <ListBlock title="明天前要练什么" items={report.next_steps ?? []} />
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
  | "generating_speaking"
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
  const [statusLines, setStatusLines] = useState<string[]>(["上传图片和音频后开始。"]);
  const [transcript, setTranscript] = useState("");
  const [assistantText, setAssistantText] = useState("");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const [playBlocked, setPlayBlocked] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const canPrepare = Boolean(imageFile && audioFile && !working);
  const visualUrl =
    (stage === "speaking" || stage === "generating_speaking") && asset?.latest_speaking_video_url
      ? asset.latest_speaking_video_url
      : stage === "listening" && asset?.listening_video_url
        ? asset.listening_video_url
      : asset?.ready_video_url || asset?.image_url || "";
  const visualIsVideo = Boolean(
    visualUrl && (visualUrl.endsWith(".mp4") || visualUrl.includes(".mp4?")),
  );

  useEffect(() => {
    return () => {
      socketRef.current?.close();
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (stage !== "speaking" || !videoRef.current) return;
    setPlayBlocked(false);
    void videoRef.current.play().catch(() => {
      setPlayBlocked(true);
      pushStatus("口型视频已生成；如果浏览器阻止自动播放，请手动点击播放。");
    });
  }, [stage, visualUrl]);

  function pushStatus(line: string) {
    setStatusLines((current) => [line, ...current].slice(0, 5));
  }

  async function waitForPreparedVideos(assetId: number) {
    const deadline = Date.now() + 120_000;
    let current = await pollFaceVideos(assetId);
    setAsset(current);
    while (current.status === "video_pending" && Date.now() < deadline) {
      pushStatus("等待 Ready 和 Listening 视频生成完成。");
      await new Promise((resolve) => window.setTimeout(resolve, 3000));
      current = await pollFaceVideos(assetId);
      setAsset(current);
    }
    if (current.status !== "video_ready") {
      throw new Error(current.error_message || "Ready/Listening 视频生成超时。");
    }
    return current;
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
      pushStatus("正在上传面试官材料。");
      const uploaded = await createFaceAsset(imageFile, audioFile);
      setAsset(uploaded);
      pushStatus("正在用参考音频登记复刻声音。");
      const voiceReady = await cloneFaceVoice(uploaded.id);
      setAsset(voiceReady);
      setStage("generating_videos");
      pushStatus("正在提交 OmniHuman Ready 和 Listening 视频任务。");
      const videoPending = await generateFaceVideos(uploaded.id);
      setAsset(videoPending);
      pushStatus("正在等待 Ready 和 Listening 视频生成完成。");
      const videoReady = await waitForPreparedVideos(uploaded.id);
      pushStatus("Ready 和 Listening 视频已生成。");
      const createdSession = await createFaceSession(videoReady.id);
      setSession(createdSession);
      setStage("ready");
      pushStatus("实时语音会话已准备好。");
    } catch (prepareError) {
      setStage("error");
      setError(prepareError instanceof Error ? prepareError.message : "无法准备数字人面试。");
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
      setError("实时语音连接失败。");
    };
    socket.onclose = () => {
      if (stage !== "error") pushStatus("实时连接已关闭。");
    };
    return socket;
  }

  function handleServerEvent(event: FaceServerEvent) {
    if (event.event === "session_started") {
      pushStatus("服务会话已启动。");
      return;
    }
    if (event.event === "asr_partial" || event.event === "asr_final") {
      setTranscript(event.text);
      return;
    }
    if (event.event === "assistant_text") {
      setAssistantText(event.text);
      return;
    }
    if (event.event === "speaking_video_pending") {
      setStage("generating_speaking");
      pushStatus("正在生成带口型的回复视频，暂时不能继续说话。");
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
      setStage("speaking");
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
    void audio.play().catch(() => pushStatus("面试官音频已就绪，但浏览器阻止了自动播放。"));
  }

  async function startListening() {
    if (!session || working || stage !== "ready") return;
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
      pushStatus("正在听你回答。说完后点击停止。");
    } catch (listenError) {
      setStage("error");
      setError(
        listenError instanceof Error
          ? listenError.message
          : "无法访问麦克风。浏览器的 HTTPS 规则可能会限制 HTTP 演示。",
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
    pushStatus("回答音频已发送。");
  }

  return (
    <div className="page-view">
      <header className="page-header">
        <div>
          <p className="eyebrow">实验功能</p>
          <h1>数字人面试</h1>
          <p className="muted">
            按住说话进行实时语音问答，可选接入 OmniHuman 视频增强。稳定主流程仍是模拟面试。
          </p>
        </div>
      </header>
      <section className="face-grid">
        <form className="panel face-setup" onSubmit={prepareAsset}>
          <h2>准备材料</h2>
          <label className="file-drop">
            <ImagePlus size={22} />
            <span>{imageFile ? imageFile.name : "面试官图片"}</span>
            <input
              accept="image/png,image/jpeg,image/webp"
              type="file"
              onChange={(event) => setImageFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <label className="file-drop">
            <FileAudio size={22} />
            <span>{audioFile ? audioFile.name : "参考音频"}</span>
            <input
              accept="audio/mpeg,audio/wav,audio/mp4,audio/ogg,audio/aac"
              type="file"
              onChange={(event) => setAudioFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <button className="primary-button" disabled={!canPrepare} type="submit">
            {working ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />}
            生成面试官
          </button>
          {error ? <p className="form-error">{error}</p> : null}
        </form>

        <section className="panel face-stage-panel">
          <div className={`face-visual face-${stage}`}>
            {visualUrl ? (
              visualIsVideo ? (
                <video
                  autoPlay
                  loop={stage !== "speaking"}
                  muted={stage !== "speaking"}
                  onEnded={() => setStage("ready")}
                  playsInline
                  ref={videoRef}
                  src={visualUrl}
                />
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
            {playBlocked && stage === "speaking" ? (
              <button
                className="secondary-button"
                onClick={() => {
                  setPlayBlocked(false);
                  void videoRef.current?.play();
                }}
                type="button"
              >
                <PlayCircle size={17} />
                播放视频
              </button>
            ) : null}
            {stage === "listening" ? (
              <button className="danger-button" onClick={stopListening} type="button">
                <Square size={17} />
                停止
              </button>
            ) : (
              <button
                className="primary-button"
                disabled={!session || working || stage !== "ready"}
                onClick={startListening}
                type="button"
              >
                <Mic size={17} />
                开始说话
              </button>
            )}
          </div>
          <div className="face-transcript-grid">
            <div>
              <h3>候选人</h3>
              <p>{transcript || "麦克风识别文本会显示在这里。"}</p>
            </div>
            <div>
              <h3>面试官</h3>
              <p>{assistantText || "面试官的实时回复会显示在这里。"}</p>
            </div>
          </div>
        </section>

        <section className="state-strip face-status-strip">
          {statusLines.map((line) => (
            <span key={line}>{line}</span>
          ))}
        </section>
        <section className="panel face-provider-panel">
          <h2>服务状态</h2>
          <dl className="status-table">
            <dt>材料</dt>
            <dd>{asset ? `#${asset.id} ${asset.status}` : "未生成"}</dd>
            <dt>声音</dt>
            <dd>{asset?.speaker_id ? "声音复刻已登记" : "等待中"}</dd>
            <dt>视频</dt>
            <dd>{asset?.error_message || asset?.provider_status || "可选"}</dd>
            <dt>会话</dt>
            <dd>{session ? `#${session.id} ${session.status}` : "未开始"}</dd>
          </dl>
        </section>
      </section>
    </div>
  );
}

function StatusPill({ stage }: { stage: FaceStage }) {
  const icon =
    stage === "listening" ? (
      <Mic size={16} />
    ) : stage === "speaking" || stage === "generating_speaking" ? (
      <Volume2 size={16} />
    ) : stage === "error" ? (
      <CircleAlert size={16} />
    ) : (
      <PlayCircle size={16} />
    );
  const labels: Record<FaceStage, string> = {
    setup: "待准备",
    preparing_voice: "生成声音中",
    generating_videos: "生成视频中",
    generating_speaking: "生成回复视频中",
    ready: "已就绪",
    listening: "聆听中",
    speaking: "回答中",
    error: "出错",
  };
  return (
    <span className={`status-pill face-status-${stage}`}>
      {icon}
      {labels[stage]}
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

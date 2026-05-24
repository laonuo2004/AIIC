"use client";

import {
  Bot,
  CheckCircle2,
  FileAudio,
  ImagePlus,
  Loader2,
  LogOut,
  MessageSquareText,
  Moon,
  RefreshCw,
  Send,
  Settings,
  Sparkles,
  Sun,
  UserRound,
  Video,
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

import {
  CandidateProfile,
  Interview,
  InterviewSummary,
  RuntimeStatus,
  User,
  createInterview,
  finishInterview,
  getInterview,
  getMe,
  getRuntimeStatus,
  listInterviews,
  login,
  logout,
  register,
  submitInterviewAnswer,
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
    profile.self_introduction.trim().length >= 10 &&
    profile.project_experience.trim().length >= 10 &&
    profile.target_direction.trim().length >= 2;

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
      });
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
            Practice project deep dives with adaptive follow-up questions, structured feedback,
            and a final review report.
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
            resetInterviewDraft={resetInterviewDraft}
            selectInterview={selectInterview}
            setAnswer={setAnswer}
            setProfile={setProfile}
            startInterview={startInterview}
            submitAnswer={submitAnswer}
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
  resetInterviewDraft: () => void;
  selectInterview: (id: number) => void;
  setAnswer: (value: string) => void;
  setProfile: (value: CandidateProfile) => void;
  startInterview: (event: FormEvent<HTMLFormElement>) => void;
  submitAnswer: (event: FormEvent<HTMLFormElement>) => void;
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
            setProfile={props.setProfile}
            startInterview={props.startInterview}
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
  setProfile: (value: CandidateProfile) => void;
  startInterview: (event: FormEvent<HTMLFormElement>) => void;
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
            The interviewer uses this context to ask one question at a time and push on weak spots.
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

      <section className="turn-list">
        {props.answeredTurns.map((turn) => (
          <article className="turn-card" key={turn.id}>
            <div className="turn-question">
              <UserRound size={17} />
              <strong>Q{turn.turn_index}. {turn.question}</strong>
            </div>
            <p className="answer-text">{turn.answer}</p>
            {turn.feedback ? <FeedbackCard feedback={turn.feedback} /> : null}
          </article>
        ))}
      </section>
    </div>
  );
}

function FeedbackCard({ feedback }: { feedback: NonNullable<Interview["turns"][number]["feedback"]> }) {
  return (
    <div className="feedback-card">
      <div className="score-pill">{feedback.score ?? "?"}/10</div>
      <ListBlock title="Strengths" items={feedback.strengths ?? []} />
      <ListBlock title="Weaknesses" items={feedback.weaknesses ?? []} />
      {feedback.advice ? <p className="advice">{feedback.advice}</p> : null}
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
      <ListBlock title="Weaknesses" items={report.weaknesses ?? []} />
      <ListBlock title="Next steps" items={report.next_steps ?? []} />
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

function FaceWorkspace() {
  return (
    <div className="page-view">
      <header className="page-header">
        <div>
          <p className="eyebrow">Experimental</p>
          <h1>Face-to-Face Interview</h1>
          <p className="muted">
            Reserved for a Volcengine-powered real-time digital interviewer experiment. The text
            interview remains the stable MVP path.
          </p>
        </div>
      </header>
      <section className="face-grid">
        <div className="upload-tile">
          <ImagePlus size={28} />
          <h2>Interviewer image</h2>
          <p>Upload entry is planned for idle, listening, and speaking visual states.</p>
        </div>
        <div className="upload-tile">
          <FileAudio size={28} />
          <h2>Reference audio</h2>
          <p>Voice cloning and real-time speech are intentionally not enabled in this MVP.</p>
        </div>
        <div className="state-strip">
          <span>Ready</span>
          <span>Listening</span>
          <span>Speaking</span>
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
            <StatusItem label="Upload limit" value={formatBytes(props.runtimeStatus?.upload_limit_bytes)} />
            <StatusItem
              label="Attachments/message"
              value={String(props.runtimeStatus?.max_attachments_per_message ?? "unknown")}
            />
            <StatusItem label="Proxy env" value={props.runtimeStatus?.proxy_enabled ? "enabled" : "not detected"} />
            <StatusItem label="Deep model" value={props.runtimeStatus?.model_strategy?.deep ?? "configured server-side"} />
            <StatusItem label="Fast model" value={props.runtimeStatus?.model_strategy?.fast ?? "configured server-side"} />
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

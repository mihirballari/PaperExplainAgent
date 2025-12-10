import { FormEvent, useMemo, useState } from "react";

type Status = "idle" | "running" | "error" | "done";

const statusColors: Record<Status, string> = {
  idle: "status-dot",
  running: "status-dot running",
  error: "status-dot error",
  done: "status-dot done",
};

function App() {
  const [apiKey, setApiKey] = useState("");
  const [topic, setTopic] = useState("");
  const [context, setContext] = useState("");
  const [useRag, setUseRag] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [statusMessage, setStatusMessage] = useState("Idle");
  const [logs, setLogs] = useState<string[]>([]);
  const [previewMessage, setPreviewMessage] = useState(
    "Output preview will appear here once a job finishes.",
  );

  const appendLog = (line: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, `[${timestamp}] ${line}`]);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!topic.trim()) {
      setStatus("error");
      setStatusMessage("Please enter a prompt.");
      appendLog("Missing prompt.");
      return;
    }

    setStatus("running");
    setStatusMessage("Submitting job to backend...");
    appendLog(
      `Submitting job: topic="${topic.trim()}", useRag=${useRag ? "on" : "off"}`,
    );

    // Example backend call (replace URL with your API endpoint)
    /*
    fetch("http://localhost:8000/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apiKey, topic, context, useRag }),
    })
      .then(async (res) => {
        const data = await res.json();
        // handle response, e.g. jobId, status, video URL
      })
      .catch((err) => {
        console.error(err);
        // handle error
      });
    */

    setTimeout(() => {
      appendLog("Simulated job accepted by backend.");
      setStatus("done");
      setStatusMessage("Job submitted (simulated).");
      setPreviewMessage(
        "Simulated response: hook the backend to render a video or thumbnail here.",
      );
    }, 500);
  };

  const statusLabel = useMemo(() => {
    switch (status) {
      case "running":
        return "Running";
      case "done":
        return "Done";
      case "error":
        return "Error";
      default:
        return "Idle";
    }
  }, [status]);

  return (
    <div className="app-shell">
      <header className="header-bar">
        <div className="header-inner">
          <span>495 Final – TheoremExplainAgent Demo</span>
          <a className="header-link" href="#" aria-label="View project on GitHub">
            View project on GitHub
          </a>
        </div>
      </header>

      <main className="page">
        <div className="max-width">
          <div className="hero">
            <h1>TheoremExplainAgent Demo</h1>
            <p>
              Lightweight viewer + prompt box. Send a request, watch the status,
              and we will render the returned video/thumbnail here once the backend
              is wired up.
            </p>
          </div>

          <div className="card">
            <h2 className="section-title">Viewer</h2>
            <div className="preview-box">
              <div className="preview-frame">
                <div className="preview-placeholder">{previewMessage}</div>
              </div>
              <div className="status-row">
                <div className="status">
                  <span className={statusColors[status]} aria-hidden="true" />
                  <span>{statusLabel}</span>
                </div>
                <span className="muted">{statusMessage}</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="minimal-form">
              <div className="inline-controls">
                <input
                  id="apiKey"
                  name="apiKey"
                  type="password"
                  className="input compact"
                  placeholder="API key (optional)"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  autoComplete="off"
                  aria-label="OpenAI API Key"
                />
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={useRag}
                    onChange={(e) => setUseRag(e.target.checked)}
                  />
                  Use RAG
                </label>
              </div>

              <textarea
                id="topic"
                name="topic"
                className="textarea"
                placeholder="Prompt: ask TEA to explain something..."
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              />

              <textarea
                id="context"
                name="context"
                className="textarea subtle"
                placeholder="Optional: add a quick note or context."
                value={context}
                onChange={(e) => setContext(e.target.value)}
              />

              <button className="button" type="submit">
                Send prompt
              </button>
            </form>

            <div className="logs-box">
              <p className="logs-title">Activity</p>
              {logs.length === 0 ? (
                <div className="empty-state">
                  No logs yet. Send a prompt to see updates.
                </div>
              ) : (
                <ul className="logs">
                  {logs.map((line, index) => (
                    <li key={`${line}-${index}`} className="log-item">
                      {line}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";

type Status = "idle" | "running" | "error" | "done";

const statusColors: Record<Status, string> = {
  idle: "status-dot",
  running: "status-dot running",
  error: "status-dot error",
  done: "status-dot done",
};

function App() {
  const [apiKey, setApiKey] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [statusMessage, setStatusMessage] = useState("Idle");
  const [clientLogs, setClientLogs] = useState<string[]>([]);
  const [scriptLogs, setScriptLogs] = useState<string[]>([]);
  const [artifacts, setArtifacts] = useState<string[]>([]);
  const [previewMessage, setPreviewMessage] = useState(
    "Output preview will appear here once a job finishes.",
  );
  const [videoUrl, setVideoUrl] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  const appendLog = (line: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setClientLogs((prev) => [...prev, `[${timestamp}] ${line}`]);
  };

  const clearPollTimeout = () => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  };

  const schedulePoll = (id: string) => {
    const poll = () => {
      fetch(`/api/status/${id}`)
        .then((res) => {
          if (!res.ok) {
            throw new Error("Failed to fetch job status.");
          }
          return res.json();
        })
        .then((data) => {
          const latestLogs: string[] = data.logs ?? [];
          const latestArtifacts: string[] = data.artifacts ?? [];
          setScriptLogs((prev) => {
            if (latestLogs.length <= prev.length) {
              return prev;
            }
            return [...prev, ...latestLogs.slice(prev.length)];
          });
          setArtifacts(latestArtifacts);
          if (data.videoUrl) {
            setVideoUrl(data.videoUrl);
          }
          const backendStatus = data.status as Status | string;

          if (backendStatus === "queued" || backendStatus === "running") {
            setStatus("running");
            setStatusMessage(data.message ?? "Processing...");
            pollTimeoutRef.current = setTimeout(poll, 4000);
            return;
          }

          clearPollTimeout();
          if (backendStatus === "done") {
            setStatus("done");
            setStatusMessage(data.message ?? "Generation complete.");
            if (data.videoUrl) {
              setPreviewMessage("Video ready—preview below.");
            } else if (data.videoPath) {
              setPreviewMessage(`Video ready at: ${data.videoPath}`);
            } else if (data.outputDir) {
              setPreviewMessage(`Artifacts saved to: ${data.outputDir}`);
            } else {
              setPreviewMessage("Generation finished. Check backend logs for artifacts.");
            }
            appendLog("Job completed.");
          } else {
            setStatus("error");
            setStatusMessage(data.message ?? "Generation failed.");
            appendLog("Job failed. Check logs for details.");
          }
        })
        .catch((error: Error) => {
          clearPollTimeout();
          setStatus("error");
          setStatusMessage(error.message);
          appendLog(`Status check failed: ${error.message}`);
        });
    };

    poll();
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    setPdfFile(file ?? null);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!pdfFile) {
      setStatus("error");
      setStatusMessage("Please select a PDF.");
      appendLog("Missing PDF file.");
      return;
    }

    clearPollTimeout();
    setClientLogs([]);
    setScriptLogs([]);
    setArtifacts([]);
    setStatus("running");
    setStatusMessage("Submitting job to backend...");
    setVideoUrl("");
    setPreviewMessage("Output preview will appear here once a job finishes.");
    appendLog(
      `Submitting job: pdf="${pdfFile.name}"}`,
    );

    const payload = new FormData();
    payload.append("pdf", pdfFile);
    if (apiKey.trim()) {
      payload.append("api_key", apiKey.trim());
    }

    fetch("/api/generate", {
      method: "POST",
      body: payload,
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error("Failed to submit job.");
        }
        return res.json();
      })
      .then((data: { jobId: string }) => {
        setJobId(data.jobId);
        appendLog(`Job accepted by backend. Job ID: ${data.jobId}`);
        setStatusMessage("Processing started...");
        schedulePoll(data.jobId);
      })
      .catch((error: Error) => {
        setStatus("error");
        setStatusMessage(error.message);
        appendLog(`Submission failed: ${error.message}`);
      });
  };

  useEffect(
    () => () => {
      clearPollTimeout();
    },
    [],
  );

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [clientLogs, scriptLogs]);

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

  const combinedLogs = useMemo(() => {
    const scriptEntries = scriptLogs.map((line) => `[generator] ${line}`);
    const merged = [...clientLogs, ...scriptEntries];
    const MAX_LOGS = 400;
    if (merged.length <= MAX_LOGS) {
      return merged;
    }
    return merged.slice(merged.length - MAX_LOGS);
  }, [clientLogs, scriptLogs]);

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
                {videoUrl ? (
                  <video key={videoUrl} className="preview-video" controls src={videoUrl}>
                    <track kind="captions" />
                  </video>
                ) : (
                  <div className="preview-placeholder">{previewMessage}</div>
                )}
              </div>
              <div className="status-row">
                <div className="status">
                  <span className={statusColors[status]} aria-hidden="true" />
                  <span>{statusLabel}</span>
                </div>
                <span className="muted truncate">{statusMessage}</span>
              </div>
              <div className="artifacts-box">
                <p className="artifacts-title">Latest Outputs</p>
                {artifacts.length === 0 ? (
                  <p className="muted">Artifacts will appear here as they are generated.</p>
                ) : (
                  <ul className="artifacts-list">
                    {artifacts.slice(-6).map((item, idx) => (
                      <li key={`${item}-${idx}`}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <form onSubmit={handleSubmit} className="minimal-form">
            <div className="inline-controls">
              <input
                id="apiKey"
                name="apiKey"
                  type="password"
                  className="input compact"
                  placeholder="API key"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  autoComplete="off"
                  aria-label="OpenAI API Key"
                />
              </div>

              <label htmlFor="pdfUpload" className="file-label">
                <span>Upload PDF</span>
                <input
                  id="pdfUpload"
                  name="pdfUpload"
                  type="file"
                  accept="application/pdf"
                  onChange={handleFileChange}
                />
              </label>
              <p className="muted">
                {pdfFile
                  ? `Selected: ${pdfFile.name} (${(pdfFile.size / 1024 / 1024).toFixed(2)} MB)`
                  : "Select a PDF research paper or document to explain."}
              </p>

              <button className="button" type="submit">
                Generate from PDF
              </button>
            </form>

            <div className="logs-box">
              <p className="logs-title">Activity</p>
              {combinedLogs.length === 0 ? (
                <div className="empty-state">
                  No logs yet. Send a prompt to see updates.
                </div>
              ) : (
                <ul className="logs">
                  {combinedLogs.map((line, index) => (
                    <li key={`${line}-${index}`} className="log-item">
                      {line}
                    </li>
                  ))}
                  <div ref={logsEndRef} />
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

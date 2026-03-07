"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import styles from "./page.module.css";
import {
  Step,
  Workbook,
  artifactUrl,
  getWorkbook,
  listSteps,
  runPrompt,
} from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string };

export default function WorkbookPage() {
  const params = useParams();
  const workbookId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const [workbook, setWorkbook] = useState<Workbook | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [activeTab, setActiveTab] = useState<"story" | "notebook">("story");
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [notebookPath, setNotebookPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workbookId) return;
    getWorkbook(workbookId)
      .then((data) => {
        setWorkbook(data);
        setNotebookPath(data.session?.notebook || data.notebook || null);
      })
      .catch((err) => setError(err.message));

    listSteps(workbookId)
      .then((data) => {
        setSteps(data);
        if (data.length > 0) {
          setCurrentStepIndex(0);
        }
      })
      .catch((err) => setError(err.message));
  }, [workbookId]);

  useEffect(() => {
    if (!workbookId) return;
    const stored = window.localStorage.getItem(`pogo:lastStep:${workbookId}`);
    if (stored) {
      const index = Number(stored);
      if (!Number.isNaN(index)) {
        setCurrentStepIndex((prev) =>
          steps.length ? Math.min(index, steps.length - 1) : prev,
        );
      }
    }
  }, [workbookId, steps.length]);

  useEffect(() => {
    if (!workbookId) return;
    window.localStorage.setItem(
      `pogo:lastStep:${workbookId}`,
      String(currentStepIndex),
    );
  }, [workbookId, currentStepIndex]);

  const currentStep = useMemo(() => steps[currentStepIndex], [steps, currentStepIndex]);

  const handleSend = async () => {
    if (!prompt.trim() || !workbookId) return;
    setError(null);
    const message = prompt.trim();
    setPrompt("");
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setIsRunning(true);
    try {
      const response = await runPrompt(workbookId, message);
      if (response.action === "clarify") {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: response.question },
        ]);
      } else {
        if (response.summary) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: response.summary },
          ]);
        }
        if (Array.isArray(response.steps)) {
          setSteps((prev) => {
            const next = [...prev, ...response.steps];
            if (prev.length === 0 && next.length > 0) {
              setCurrentStepIndex(0);
            }
            return next;
          });
        }
        if (response.notebook) {
          setNotebookPath(response.notebook);
        }
      }
    } catch (err: any) {
      setError(err.message || "Something went wrong.");
    } finally {
      setIsRunning(false);
    }
  };

  const canGoBack = currentStepIndex > 0;
  const canGoForward = currentStepIndex < steps.length - 1;

  const statusText = () => {
    if (isRunning) return "generating...";
    if (steps.length === 0) return "no steps yet";
    if (canGoForward) return "more steps available";
    return "finished";
  };

  const renderPreviewTable = (rows?: Record<string, unknown>[]) => {
    if (!rows || rows.length === 0) return <p className={styles.storyMeta}>No preview rows.</p>;
    const columns = Object.keys(rows[0] || {});
    return (
      <table className={styles.previewTable}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 6).map((row, idx) => (
            <tr key={idx}>
              {columns.map((col) => (
                <td key={col}>{String(row[col] ?? "")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <Link href="/" className={styles.backLink}>
            ← Back to workbooks
          </Link>
          <h1>{workbook?.name || "Workbook"}</h1>
        </div>
        <div className={styles.badge}>One dataset · live notebook</div>
      </header>

      <section className={styles.workspace}>
        <div className={styles.panel}>
          <div className={styles.chatHeader}>
            <strong>Chat with data</strong>
            <span className={styles.badge}>{steps.length} steps</span>
          </div>
          <div className={styles.chatBody}>
            {messages.length === 0 && (
              <p className={styles.storyMeta}>
                Ask a question to start the story. Clarifications will appear here.
              </p>
            )}
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`${styles.message} ${
                  msg.role === "user" ? styles.userMessage : styles.assistantMessage
                }`}
              >
                {msg.content}
              </div>
            ))}
          </div>
          <div className={styles.chatInput}>
            <textarea
              rows={2}
              placeholder="Ask a question about the dataset..."
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
            <button onClick={handleSend} disabled={isRunning}>
              {isRunning ? "Working" : "Send"}
            </button>
          </div>
          {error && <p className={styles.storyMeta}>{error}</p>}
        </div>

        <div className={styles.panel}>
          <div className={styles.tabs}>
            <button
              className={`${styles.tabButton} ${
                activeTab === "story" ? styles.tabButtonActive : ""
              }`}
              onClick={() => setActiveTab("story")}
            >
              Story
            </button>
            <button
              className={`${styles.tabButton} ${
                activeTab === "notebook" ? styles.tabButtonActive : ""
              }`}
              onClick={() => setActiveTab("notebook")}
            >
              Notebook
            </button>
          </div>

          {activeTab === "story" && (
            <div className={styles.storyPanel}>
              <div className={styles.storyNav}>
                <button
                  className={styles.navButton}
                  onClick={() => setCurrentStepIndex((idx) => Math.max(0, idx - 1))}
                  disabled={!canGoBack}
                >
                  ↑ Step back
                </button>
                <div className={styles.storyMeta}>
                  Step {steps.length === 0 ? 0 : currentStepIndex + 1} of {steps.length}
                </div>
              </div>

              {currentStep ? (
                <div className={styles.storyCard}>
                  <div className={styles.storyTitle}>
                    {currentStep.title || "Analysis step"}
                  </div>
                  {currentStep.reasoning && (
                    <p className={styles.storyMeta}>{currentStep.reasoning}</p>
                  )}

                  {currentStep.sql && (
                    <div className={styles.storySection}>
                      <strong>SQL</strong>
                      <pre className={styles.sqlBlock}>{currentStep.sql}</pre>
                    </div>
                  )}

                  <div className={styles.storySection}>
                    <strong>Preview</strong>
                    {renderPreviewTable(currentStep.preview_rows)}
                  </div>

                  {currentStep.plots && currentStep.plots.length > 0 && (
                    <div className={styles.storySection}>
                      <strong>{currentStep.viz_title || "Visualization"}</strong>
                      <div className={styles.plotGrid}>
                        {currentStep.plots.map((plot) => (
                          <img
                            key={plot}
                            src={artifactUrl(workbookId || "", plot)}
                            alt={currentStep.viz_title || "Plot"}
                          />
                        ))}
                      </div>
                      {currentStep.viz_caption && (
                        <p className={styles.storyMeta}>{currentStep.viz_caption}</p>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className={styles.storyMeta}>No story steps yet.</p>
              )}

              <div className={styles.statusBar}>
                <span>{statusText()}</span>
                <button
                  className={styles.navButton}
                  onClick={() =>
                    setCurrentStepIndex((idx) =>
                      Math.min(steps.length - 1, idx + 1),
                    )
                  }
                  disabled={!canGoForward}
                >
                  ↓ Next step
                </button>
              </div>
            </div>
          )}

          {activeTab === "notebook" && (
            <div className={styles.notebookPanel}>
              {notebookPath ? (
                <>
                  <p className={styles.storyMeta}>
                    Notebook is generated as steps complete. Download the latest file or
                    refresh after new prompts.
                  </p>
                  {isRunning && (
                    <p className={styles.storyMeta}>Notebook still generating...</p>
                  )}
                  <a href={artifactUrl(workbookId || "", notebookPath)}>
                    Download notebook
                  </a>
                </>
              ) : (
                <p className={styles.storyMeta}>Notebook still generating...</p>
              )}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";
import { Workbook, createWorkbook, listWorkbooks, uploadDataset } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [workbooks, setWorkbooks] = useState<Workbook[]>([]);
  const [name, setName] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listWorkbooks()
      .then(setWorkbooks)
      .catch((err) => setError(err.message));
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("Give the notebook a name before uploading a dataset.");
      return;
    }
    if (files.length === 0) {
      setError("Upload at least one dataset file.");
      return;
    }
    setLoading(true);
    try {
      const workbook = await createWorkbook(name.trim());
      await uploadDataset(workbook.id, files);
      router.push(`/workbooks/${workbook.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create workbook.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div>
          <h1>pogo workbooks</h1>
          <p>
            Create a named notebook, attach a dataset, and start chatting your way
            through data stories. Each step becomes a narrative card and a notebook cell.
          </p>
        </div>
      </section>

      <section className={styles.panel}>
        <h2>Create a workbook</h2>
        <p className={styles.notice}>
          One dataset per workbook to start. CSV, TSV, Excel, and Parquet are supported.
        </p>
        <form onSubmit={handleSubmit}>
          <div className={styles.formRow}>
            <input
              className={styles.input}
              placeholder="Workbook name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
            <input
              className={styles.fileInput}
              type="file"
              multiple
              onChange={(event) =>
                setFiles(event.target.files ? Array.from(event.target.files) : [])
              }
            />
            <button className={styles.button} type="submit" disabled={loading}>
              {loading ? "Creating..." : "Create & open"}
            </button>
          </div>
        </form>
        {error && <p className={styles.error}>{error}</p>}
      </section>

      <section className={styles.panel}>
        <h2>Recent workbooks</h2>
        <div className={styles.grid}>
          {workbooks.length === 0 && (
            <p className={styles.notice}>No workbooks yet. Create the first one.</p>
          )}
          {workbooks.map((workbook) => (
            <div key={workbook.id} className={styles.workbookCard}>
              <div className={styles.cardTitle}>{workbook.name}</div>
              <div className={styles.meta}>
                <span>{new Date(workbook.created_at).toLocaleString()}</span>
                <span>
                  {workbook.dataset_attached ? "Dataset ready" : "Awaiting dataset"}
                </span>
              </div>
              <div className={styles.meta}>
                <span>Steps: {workbook.step_count ?? 0}</span>
                <span>{workbook.dataset_files?.length ?? 0} files</span>
              </div>
              <button
                className={styles.button}
                onClick={() => router.push(`/workbooks/${workbook.id}`)}
              >
                Open workbook
              </button>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

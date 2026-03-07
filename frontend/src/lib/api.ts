export type Step = {
  id: string;
  index: number;
  title?: string;
  reasoning?: string;
  sql?: string;
  preview_rows?: Record<string, unknown>[];
  row_count?: number;
  table_path?: string;
  plots?: string[];
  viz_title?: string;
  viz_caption?: string;
  status?: string;
  error?: string;
  created_at?: string;
};

export type Workbook = {
  id: string;
  name: string;
  created_at: string;
  dataset_attached?: boolean;
  dataset_files?: string[];
  step_count?: number;
  notebook?: string;
  session?: {
    dataset?: Record<string, unknown>;
    step_count?: number;
    notebook?: string;
  };
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function listWorkbooks(): Promise<Workbook[]> {
  return apiFetch<Workbook[]>("/workbooks");
}

export async function createWorkbook(name: string): Promise<Workbook> {
  return apiFetch<Workbook>("/workbooks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export async function uploadDataset(
  workbookId: string,
  files: File[],
): Promise<{ notebook: string }>{
  const data = new FormData();
  files.forEach((file) => data.append("files", file));
  const res = await fetch(`${API_BASE}/workbooks/${workbookId}/dataset`, {
    method: "POST",
    body: data,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function getWorkbook(workbookId: string): Promise<Workbook> {
  return apiFetch<Workbook>(`/workbooks/${workbookId}`);
}

export async function listSteps(workbookId: string): Promise<Step[]> {
  return apiFetch<Step[]>(`/workbooks/${workbookId}/steps`);
}

export async function runPrompt(
  workbookId: string,
  prompt: string,
): Promise<any> {
  return apiFetch(`/workbooks/${workbookId}/prompts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
}

export function artifactUrl(workbookId: string, relativePath: string): string {
  const trimmed = relativePath.replace(/^\/+/, "");
  return `${API_BASE}/artifacts/${workbookId}/${trimmed}`;
}

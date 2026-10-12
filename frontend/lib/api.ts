export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type DocumentInfo = {
  id: string;
  filename: string;
  n_pages: number;
  n_chunks: number;
  created_at: string;
};

export type Source = {
  document_id: string;
  filename: string;
  page: number;
  snippet: string;
  score: number;
};

export type ChatResponse = { answer: string; sources: Source[] };

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = j.detail ?? msg;
    } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const listDocuments = () =>
  fetch(`${API_URL}/api/documents`, { cache: "no-store" }).then(handle<DocumentInfo[]>);

export function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);
  return fetch(`${API_URL}/api/documents`, { method: "POST", body: form }).then(
    handle<DocumentInfo>
  );
}

export const deleteDocument = (id: string) =>
  fetch(`${API_URL}/api/documents/${id}`, { method: "DELETE" }).then(handle<void>);

export const askQuestion = (question: string, documentIds: string[] | null) =>
  fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, document_ids: documentIds }),
  }).then(handle<ChatResponse>);

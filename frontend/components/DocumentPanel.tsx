"use client";

import { useRef, useState } from "react";
import { DocumentInfo, deleteDocument, uploadDocument } from "@/lib/api";

type Props = {
  docs: DocumentInfo[];
  selected: string[];
  setSelected: (ids: string[]) => void;
  onChange: () => void;
  error: string | null;
};

export default function DocumentPanel({ docs, selected, setSelected, onChange, error }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [drag, setDrag] = useState(false);

  async function handleFiles(files: FileList | File[]) {
    const errs: string[] = [];
    for (const f of Array.from(files)) {
      setBusy(`Indexation de ${f.name}…`);
      try {
        await uploadDocument(f);
      } catch (e) {
        errs.push(`${f.name} : ${(e as Error).message}`);
      }
    }
    setBusy(null);
    setErrors(errs);
    onChange();
  }

  const toggle = (id: string) =>
    setSelected(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);

  return (
    <aside className="panel">
      <h2>Documents</h2>

      <div
        className={`dropzone ${drag ? "drag" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        {busy ?? "Glisse un PDF ici ou clique pour uploader"}
        <small>PDF, DOCX, TXT, MD</small>
        <input
          ref={inputRef}
          type="file"
          hidden
          multiple
          accept=".pdf,.docx,.txt,.md"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
      </div>

      {error && <p className="error">{error}</p>}
      {errors.map((e) => (
        <p key={e} className="error">
          {e}
        </p>
      ))}

      <ul className="doclist">
        {docs.map((d) => (
          <li key={d.id}>
            <label>
              <input
                type="checkbox"
                checked={selected.includes(d.id)}
                onChange={() => toggle(d.id)}
              />
              <span className="docname">
                {d.filename}
                <small>
                  {d.n_pages} p. · {d.n_chunks} chunks
                </small>
              </span>
            </label>
            <button
              className="icon"
              title="Supprimer"
              onClick={async () => {
                await deleteDocument(d.id);
                setSelected(selected.filter((x) => x !== d.id));
                onChange();
              }}
            >
              ✕
            </button>
          </li>
        ))}
        {docs.length === 0 && <li className="muted">Aucun document.</li>}
      </ul>
      <p className="muted small">
        {selected.length
          ? `Recherche limitée à ${selected.length} document(s).`
          : "Aucune sélection : recherche dans tous les documents."}
      </p>
    </aside>
  );
}

"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Source, askQuestion } from "@/lib/api";

type Message = { role: "user" | "assistant"; text: string; sources?: Source[]; error?: boolean };

export default function Chat({
  documentIds,
  hasDocs,
}: {
  documentIds: string[] | null;
  hasDocs: boolean;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const res = await askQuestion(q, documentIds);
      setMessages((m) => [...m, { role: "assistant", text: res.answer, sources: res.sources }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: (err as Error).message, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="chat">
      <div className="messages">
        {messages.length === 0 && (
          <div className="empty">
            <h1>AI Document Assistant</h1>
            <p>
              {hasDocs
                ? "Pose une question sur tes documents."
                : "Upload un document à gauche pour commencer."}
            </p>
            <p className="muted">
              Ex : « How many days of annual leave can an employee take? »
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role} ${m.error ? "err" : ""}`}>
            <div className="bubble">{m.text}</div>
            {m.sources && m.sources.length > 0 && (
              <div className="sources">
                <strong>Sources :</strong>
                <ul>
                  {m.sources.map((s) => (
                    <li key={`${s.document_id}-${s.page}`} title={s.snippet}>
                      {s.filename.replace(/\.[^.]+$/, "")} - page {s.page}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="msg assistant">
            <div className="bubble muted">Recherche en cours…</div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form className="inputbar" onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Pose ta question…"
          disabled={!hasDocs}
        />
        <button type="submit" disabled={loading || !input.trim() || !hasDocs}>
          Envoyer
        </button>
      </form>
    </section>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import Chat from "@/components/Chat";
import DocumentPanel from "@/components/DocumentPanel";
import { DocumentInfo, listDocuments } from "@/lib/api";

export default function Home() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setDocs(await listDocuments());
      setError(null);
    } catch (e) {
      setError(`Backend injoignable : ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <main className="layout">
      <DocumentPanel
        docs={docs}
        selected={selected}
        setSelected={setSelected}
        onChange={refresh}
        error={error}
      />
      <Chat documentIds={selected.length ? selected : null} hasDocs={docs.length > 0} />
    </main>
  );
}

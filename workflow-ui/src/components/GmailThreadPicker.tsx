import { useEffect, useState } from "react";

interface GmailThread {
  thread_id: string;
  from: string;
  subject: string;
  snippet: string;
  last_message_at: string;
}

interface GmailThreadPickerProps {
  onSelectThread: (threadId: string) => void;
}

export default function GmailThreadPicker({
  onSelectThread,
}: GmailThreadPickerProps) {
  const [threads, setThreads] = useState<GmailThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedThread, setSelectedThread] = useState<string | null>(null);

  useEffect(() => {
    async function fetchThreads() {
      try {
        const res = await fetch(
          "http://localhost:8000/gmail/threads?limit=5"
        );

        if (!res.ok) {
          throw new Error("Failed to load Gmail threads");
        }

        const data = await res.json();
        setThreads(data);
      } catch (e: any) {
        setError(e.message || "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    fetchThreads();
  }, []);

  if (loading) {
    return <p>📥 Loading recent emails…</p>;
  }

  if (error) {
    return (
      <div>
        <p>❌ Failed to load emails</p>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div>
      <h3>Select an email thread</h3>

      <ul style={{ listStyle: "none", padding: 0 }}>
        {threads.map((t) => (
          <li
            key={t.thread_id}
            onClick={() => setSelectedThread(t.thread_id)}
            style={{
              padding: "12px",
              marginBottom: "8px",
              border: "1px solid #ddd",
              borderRadius: "6px",
              cursor: "pointer",
              background:
                selectedThread === t.thread_id ? "#eef6ff" : "white",
            }}
          >
            <p>
              <strong>{t.subject || "(No subject)"}</strong>
            </p>
            <p style={{ fontSize: "0.9em", color: "#555" }}>
              From: {t.from}
            </p>
            <p style={{ fontSize: "0.8em", color: "#888" }}>
              {new Date(t.last_message_at).toLocaleString()}
            </p>
          </li>
        ))}
      </ul>

      <button
        disabled={!selectedThread}
        onClick={() => selectedThread && onSelectThread(selectedThread)}
      >
        Continue
      </button>
    </div>
  );
}

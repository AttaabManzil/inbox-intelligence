import { useEffect, useState } from "react";

interface GmailThread {
  thread_id: string;
  from: string;
  subject: string;
  snippet: string;
  last_message_at: string;
}

interface GmailThreadPickerProps {
  onSelectThread: (gmailThreadId: string) => void;
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
          "http://localhost:8000/gmail/threads?limit=10"
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

  /* ------------------ States ------------------ */

  if (loading) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm text-sm text-gray-500">
        Loading recent conversations…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
        <p className="font-medium">Failed to load emails</p>
        <p>{error}</p>
      </div>
    );
  }

  /* ------------------ UI ------------------ */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900">
          Choose a conversation
        </h2>
        <p className="text-sm text-gray-500">
          Select an email thread to draft a reply
        </p>
      </div>

      {/* Thread list */}
      <div className="grid gap-3">
        {threads.map((t) => {
          const selected = selectedThread === t.thread_id;

          return (
            <div
              key={t.thread_id}
              onClick={() => setSelectedThread(t.thread_id)}
              className={`
                group cursor-pointer rounded-xl border bg-white p-4 transition
                ${
                  selected
                    ? "border-black shadow-md"
                    : "border-gray-200 hover:-translate-y-[1px] hover:shadow-md"
                }
              `}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <p className="font-medium text-gray-900">
                    {t.subject || "(No subject)"}
                  </p>

                  <p className="text-sm text-gray-500 truncate">
                    From: {t.from}
                  </p>

                  {t.snippet && (
                    <p className="text-sm text-gray-400 line-clamp-2">
                      {t.snippet}
                    </p>
                  )}
                </div>

                {selected && (
                  <span className="text-xs font-medium text-black">
                    Selected
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Action */}
      <button
        disabled={!selectedThread}
        onClick={() => onSelectThread(selectedThread!)}
        className="
          w-full rounded-xl bg-black py-3 text-sm font-medium text-white
          transition hover:opacity-90
          disabled:cursor-not-allowed disabled:bg-gray-300
        "
      >
        Continue
      </button>
    </div>
  );
}

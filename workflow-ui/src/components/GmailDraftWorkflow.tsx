import { useState, useEffect } from "react";

interface GmailDraftWorkflowProps {
  initialDraft: string;
  onSaveDraft: (draft: string) => Promise<void>;
  onSendEmail: () => Promise<void>; // 🔥 no draft argument needed
  saving?: boolean;
}

export default function GmailDraftWorkflow({
  initialDraft,
  onSaveDraft,
  onSendEmail,
  saving = false,
}: GmailDraftWorkflowProps) {
  const [draft, setDraft] = useState(initialDraft);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 🔁 keep textarea in sync if backend updates draft
  useEffect(() => {
    setDraft(initialDraft);
  }, [initialDraft]);

  async function handleSave() {
    try {
      setLoading(true);
      setError(null);
      await onSaveDraft(draft);
      alert("Draft saved to Gmail");
    } catch {
      setError("Failed to save draft");
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    try {
      setLoading(true);
      setError(null);
      await onSendEmail(); // ✅ backend already has draft
      alert("Email sent successfully");
    } catch {
      setError("Failed to send email");
    } finally {
      setLoading(false);
    }
  }

  const disabled = loading || saving;

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Edit Draft</h2>

      {error && (
        <div className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-600">
          {error}
        </div>
      )}

      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={14}
        className="w-full rounded border p-3 text-sm"
      />

      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={disabled}
          className="rounded bg-gray-800 px-4 py-2 text-white disabled:opacity-50"
        >
          Save to Drafts
        </button>

        <button
          onClick={handleSend}
          disabled={disabled}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
        >
          Send Email
        </button>
      </div>
    </div>
  );
}

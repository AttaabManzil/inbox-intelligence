import { useNavigate } from "react-router-dom";
import { useState } from "react";
import GmailThreadPicker from "../components/GmailThreadPicker";

type CreateWorkflowResponse = {
  workflow_id: string;
};

export default function GmailDraftPage() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // --------------------------------------------------
  // Create workflow AFTER thread selection
  // --------------------------------------------------
  async function handleSelectThread(gmailThreadId: string) {
    try {
      setLoading(true);
      setError(null);

      const res = await fetch("http://localhost:8000/workflows", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: `gmail:${gmailThreadId}`,
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to create workflow");
      }

      const data: CreateWorkflowResponse = await res.json();

      // ✅ SINGLE SOURCE OF TRUTH:
      // from here onward we ONLY use workflowId
      navigate(`/gmail/context/${data.workflow_id}`);
    } catch (err) {
      setError("Failed to create workflow. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  // --------------------------------------------------
  // UI
  // --------------------------------------------------
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="text-2xl font-semibold text-gray-900">
          Draft Gmail Reply
        </h1>

        <p className="mt-1 text-sm text-gray-500">
          Select an email conversation to begin
        </p>

        {error && (
          <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <div className="mt-6 rounded-xl bg-white p-6 shadow">
          {loading ? (
            <p className="text-sm text-gray-500">
              Creating workflow…
            </p>
          ) : (
            <GmailThreadPicker onSelectThread={handleSelectThread} />
          )}
        </div>
      </div>
    </div>
  );
}

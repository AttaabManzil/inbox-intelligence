import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import GmailDraftWorkflow from "../components/GmailDraftWorkflow";

export default function GmailDraftReviewPage() {
  const { workflowId } = useParams();
  const [workflow, setWorkflow] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  

  // ---------------- LOAD WORKFLOW ----------------
  useEffect(() => {
    async function loadWorkflow() {
      try {
        const res = await fetch(
          `http://localhost:8000/workflows/${workflowId}`
        );

        if (!res.ok) {
          throw new Error("Failed to load workflow");
        }

        const data = await res.json();
        setWorkflow(data);
      } catch (e: any) {
        setError(e.message || "Failed to load draft");
      }
    }

    loadWorkflow();
  }, [workflowId]);

  // ---------------- SAVE TO GMAIL DRAFTS ----------------
  async function saveDraft() {
    if (!workflowId) return;

    try {
      setSaving(true);

      const res = await fetch(
        `http://localhost:8000/workflows/${workflowId}/save-gmail-draft`,
        {
          method: "POST",
        }
      );

      if (!res.ok) {
        throw new Error("Failed to save Gmail draft");
      }

      alert("✅ Draft saved to Gmail!");
    } catch (e) {
      alert("❌ Failed to save draft");
    } finally {
      setSaving(false);
    }
  }

  // ---------------- SEND EMAIL (NOT WIRED YET) ----------------
  async function sendEmail() {
    const res = await fetch(
      `http://localhost:8000/workflows/${workflowId}/send-email`,
      {
        method: "POST",
      }
    );

    if (!res.ok) {
      throw new Error("Failed to send email");
    }

    alert("Email sent successfully");
}


  // ---------------- UI STATES ----------------
  if (error) {
    return <p className="p-6 text-red-600">{error}</p>;
  }

  if (!workflow) {
    return <p className="p-6">Loading draft…</p>;
  }

  const draftText =
    workflow.ai_output?.draft?.body || "No draft generated.";

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-4xl rounded-xl bg-white p-6">
        <GmailDraftWorkflow
          initialDraft={draftText}
          onSaveDraft={saveDraft}
          onSendEmail={sendEmail}
          saving={saving}
        />
      </div>
    </div>
  );
}

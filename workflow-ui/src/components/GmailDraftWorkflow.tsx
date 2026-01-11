import { useEffect, useState } from "react";

/**
 * UI states that mirror backend reality
 */
type UiState =
  | "WAITING_FOR_AI"
  | "DRAFT_READY"
  | "APPROVING"
  | "DONE"
  | "ERROR";

interface GmailDraftWorkflowProps {
  workflowId: string;
}

export default function GmailDraftWorkflow({
  workflowId,
}: GmailDraftWorkflowProps) {
  const [workflow, setWorkflow] = useState<any>(null);
  const [uiState, setUiState] = useState<UiState>("WAITING_FOR_AI");
  const [error, setError] = useState<string | null>(null);

  // --------------------------------------------------
  // Poll workflow until draft is ready
  // --------------------------------------------------
  useEffect(() => {
    if (!workflowId) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(
          `http://localhost:8000/workflows/${workflowId}`
        );

        if (!res.ok) {
          throw new Error("Failed to fetch workflow");
        }

        const data = await res.json();
        setWorkflow(data);

        const draftReady =
          data.state === "WAITING_FOR_APPROVAL" &&
          data.ai_output?.type === "gmail_draft" &&
          data.ai_output?.draft?.body;

        if (draftReady) {
          setUiState("DRAFT_READY");
          clearInterval(interval);
        }
      } catch (e: any) {
        setError(e.message || "Unknown error");
        setUiState("ERROR");
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [workflowId]);

  // --------------------------------------------------
  // Approve draft → create Gmail draft
  // --------------------------------------------------
  async function approveDraft() {
    try {
      setUiState("APPROVING");

      const res = await fetch(
        `http://localhost:8000/workflows/${workflowId}/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            decision: "approved",
            reviewer: "user",
          }),
        }
      );

      if (!res.ok) {
        throw new Error("Approval failed");
      }

      setUiState("DONE");
    } catch (e: any) {
      setError(e.message || "Approval error");
      setUiState("ERROR");
    }
  }

  // --------------------------------------------------
  // Reject draft
  // --------------------------------------------------
  async function rejectDraft() {
    try {
      setUiState("APPROVING");

      await fetch(
        `http://localhost:8000/workflows/${workflowId}/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            decision: "rejected",
            reviewer: "user",
            notes: "Rejected by user",
          }),
        }
      );

      setUiState("DONE");
    } catch (e: any) {
      setError(e.message || "Rejection error");
      setUiState("ERROR");
    }
  }

  // --------------------------------------------------
  // UI Rendering
  // --------------------------------------------------

  if (uiState === "WAITING_FOR_AI") {
    return (
      <div>
        <p>⏳ Generating draft…</p>
        <p>This usually takes a few seconds.</p>
      </div>
    );
  }

  if (uiState === "DRAFT_READY") {
    const draft = workflow.ai_output.draft;

    return (
      <div>
        <h3>📧 Draft Preview</h3>

        <p>
          <strong>To:</strong> {draft.to}
        </p>

        <p>
          <strong>Subject:</strong> {draft.subject}
        </p>

        <pre
          style={{
            whiteSpace: "pre-wrap",
            background: "#f6f6f6",
            padding: "12px",
            borderRadius: "6px",
          }}
        >
          {draft.body}
        </pre>

        <div style={{ marginTop: "12px" }}>
          <button onClick={approveDraft}>Approve Draft</button>
          <button onClick={rejectDraft} style={{ marginLeft: "8px" }}>
            Reject
          </button>
        </div>
      </div>
    );
  }

  if (uiState === "APPROVING") {
    return <p>📬 Creating Gmail draft…</p>;
  }

  if (uiState === "DONE") {
    return <p>✅ Draft created in Gmail → Drafts</p>;
  }

  if (uiState === "ERROR") {
    return (
      <div>
        <p>❌ Something went wrong</p>
        <p>{error}</p>
      </div>
    );
  }

  return null;
}

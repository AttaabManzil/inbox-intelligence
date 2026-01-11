import { useState } from "react";
import GmailThreadPicker from "./components/GmailThreadPicker";
import GmailDraftWorkflow from "./components/GmailDraftWorkflow";

export default function GmailDraftPage() {
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [userContext, setUserContext] = useState("");
  const [workflowId, setWorkflowId] = useState(null);
  const [loading, setLoading] = useState(false);

  async function createWorkflow() {
    setLoading(true);

    const res = await fetch("http://localhost:8000/workflows", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: `gmail:${selectedThreadId}`,
        user_context: userContext,
      }),
    });

    const data = await res.json();
    setWorkflowId(data.workflow_id);
    setLoading(false);
  }

  // ----------------------------
  // STEP 1: Pick thread
  // ----------------------------
  if (!selectedThreadId) {
    return <GmailThreadPicker onSelectThread={setSelectedThreadId} />;
  }

  // ----------------------------
  // STEP 2: Add instructions
  // ----------------------------
  if (!workflowId) {
    return (
      <div>
        <h3>Optional instructions</h3>

        <textarea
          placeholder="E.g. Keep it short and friendly, ask for a call next week"
          value={userContext}
          onChange={(e) => setUserContext(e.target.value)}
          rows={4}
          style={{ width: "100%" }}
        />

        <br />
        <br />

        <button onClick={createWorkflow} disabled={loading}>
          {loading ? "Generating…" : "Generate Draft"}
        </button>
      </div>
    );
  }

  // ----------------------------
  // STEP 3: Draft + approval
  // ----------------------------
  return <GmailDraftWorkflow workflowId={workflowId} />;
}

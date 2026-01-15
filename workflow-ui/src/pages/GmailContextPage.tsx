import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

// ============================================
// TYPES
// ============================================

interface Message {
  from: string;
  date?: string;
  body: string;
}

interface Workflow {
  ai_output: {
    thread: {
      messages: Message[];
      subject?: string;
      to?: string;
    };
  };
  id: string;
  status: string;
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function extractName(from: string): string {
  // "John Doe <john@example.com>" -> "John Doe"
  const match = from.match(/^([^<]+)</);
  return match ? match[1].trim() : from;
}

function extractEmail(from: string): string {
  // "John Doe <john@example.com>" -> "john@example.com"
  const match = from.match(/<([^>]+)>/);
  return match ? match[1] : from;
}

function isSystemEmail(from: string): boolean {
  const lower = from.toLowerCase();
  return (
    lower.includes("noreply") ||
    lower.includes("no-reply") ||
    lower.includes("mailer-daemon") ||
    lower.includes("postmaster")
  );
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "";
  try {
    const date = new Date(dateStr);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

// ============================================
// COMPONENTS
// ============================================

function MessageCard({ message, index }: { message: Message; index: number }) {
  const [isCollapsed, setIsCollapsed] = useState(index !== 0); // Collapse all except first
  const isSystem = isSystemEmail(message.from);
  const name = extractName(message.from);
  const email = extractEmail(message.from);

  // Convert URLs to clickable links
  const bodyWithLinks = message.body.replace(
    /(https?:\/\/[^\s]+)/g,
    '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">$1</a>'
  );

  return (
    <div
      className={`border rounded-lg p-4 mb-3 transition-all ${
        isSystem ? "bg-gray-50 border-gray-200" : "bg-white border-gray-300"
      }`}
    >
      {/* Header */}
      <div
        className="flex items-start justify-between cursor-pointer"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-gray-900">{name}</span>
            {isSystem && (
              <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">
                System
              </span>
            )}
          </div>
          <div className="text-xs text-gray-500 mt-0.5">
            {email} • {formatDate(message.date)}
          </div>
        </div>

        {/* Collapse toggle */}
        <button className="text-gray-400 hover:text-gray-600">
          {isCollapsed ? (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          )}
        </button>
      </div>

      {/* Body */}
      {!isCollapsed && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <div
            className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed"
            dangerouslySetInnerHTML={{ __html: bodyWithLinks }}
          />
        </div>
      )}
    </div>
  );
}

// ============================================
// MAIN COMPONENT
// ============================================

export default function GmailContextPage() {
  const { workflowId } = useParams();
  const navigate = useNavigate();

  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [instructions, setInstructions] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);

  useEffect(() => {
    async function init() {
      if (!workflowId) {
        setError("Invalid workflow ID");
        setLoading(false);
        return;
      }

      try {
        // Load conversation
        const loadRes = await fetch(
          `http://localhost:8000/workflows/${workflowId}/load-conversation`,
          { method: "POST" }
        );

        if (!loadRes.ok) {
          throw new Error("Failed to load conversation");
        }

        // Fetch workflow data
        const res = await fetch(`http://localhost:8000/workflows/${workflowId}`);

        if (!res.ok) {
          throw new Error("Failed to fetch workflow");
        }

        const data: Workflow = await res.json();

        if (!data.ai_output?.thread?.messages) {
          throw new Error("No conversation data found");
        }

        setWorkflow(data);
      } catch (e: any) {
        setError(e.message || "Failed to load conversation");
      } finally {
        setLoading(false);
      }
    }

    init();
  }, [workflowId]);

  async function generateDraft() {
    if (!workflowId) return;

    setGenerating(true);
    setDraftError(null);

    try {
      const res = await fetch(
        `http://localhost:8000/workflows/${workflowId}/generate-draft`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_context: instructions,
          }),
        }
      );

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Draft generation failed");
      }

      navigate(`/gmail/draft/review/${workflowId}`);
    } catch (e: any) {
      setDraftError(e.message || "Failed to generate draft");
    } finally {
      setGenerating(false);
    }
  }

  // ============================================
  // UI STATES
  // ============================================

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <p className="mt-3 text-gray-600">Loading conversation…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h3 className="text-red-800 font-semibold mb-2">Error Loading Conversation</h3>
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => navigate("/gmail/draft")}
            className="mt-4 text-sm text-red-700 hover:text-red-900 underline"
          >
            ← Back to email selection
          </button>
        </div>
      </div>
    );
  }

  const messages = workflow?.ai_output?.thread?.messages || [];
  const subject = workflow?.ai_output?.thread?.subject || "Conversation";

  // ============================================
  // MAIN UI
  // ============================================

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate("/gmail/draft")}
            className="text-sm text-gray-600 hover:text-gray-900 mb-2"
          >
            ← Back
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{subject}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {messages.length} message{messages.length !== 1 ? "s" : ""}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* LEFT: Conversation */}
          <div className="bg-gray-100 rounded-xl p-6 overflow-y-auto max-h-[75vh]">
            <h2 className="font-semibold text-lg mb-4">Conversation</h2>
            {messages.length === 0 ? (
              <p className="text-gray-500 text-sm">No messages to display</p>
            ) : (
              messages.map((message, index) => (
                <MessageCard key={index} message={message} index={index} />
              ))
            )}
          </div>

          {/* RIGHT: Instructions */}
          <div className="bg-white rounded-xl p-6 border border-gray-200">
            <h2 className="font-semibold text-lg mb-4">Instructions to AI</h2>

            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              rows={10}
              className="w-full border border-gray-300 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              placeholder="Tell the AI how you want to reply...

Examples:
• Reply professionally thanking them
• Ask for more details about their proposal
• Decline politely and suggest alternatives"
            />

            {draftError && (
              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{draftError}</p>
              </div>
            )}

            <button
              onClick={generateDraft}
              disabled={generating || !instructions.trim()}
              className="mt-4 w-full bg-gray-900 text-white px-4 py-3 rounded-lg font-medium
                hover:bg-gray-800 transition-colors
                disabled:bg-gray-300 disabled:cursor-not-allowed disabled:text-gray-500"
            >
              {generating ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Generating Draft...
                </span>
              ) : (
                "Generate Draft →"
              )}
            </button>

            <p className="text-xs text-gray-500 mt-3">
              The AI will draft a reply based on the conversation above and your instructions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
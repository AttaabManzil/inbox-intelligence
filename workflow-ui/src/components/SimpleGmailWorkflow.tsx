import { useState, useEffect } from 'react';

interface Message {
  from: string;
  date: string;
  body: string;
}

interface Thread {
  thread_id: string;
  to: string;
  subject: string;
  message_id: string;
  references: string;
  messages: Message[];
}

interface SimpleGmailWorkflowProps {
  threadId: string;
  onBack: () => void;
}

export default function SimpleGmailWorkflow({ threadId, onBack }: SimpleGmailWorkflowProps) {
  const [loading, setLoading] = useState(true);
  const [thread, setThread] = useState<Thread | null>(null);
  const [draftBody, setDraftBody] = useState('');
  const [userContext, setUserContext] = useState('');
  const [step, setStep] = useState<'context' | 'review' | 'sent'>('context');
  const [generatingDraft, setGeneratingDraft] = useState(false);

  // Load conversation immediately when component mounts
  useEffect(() => {
    async function loadThread() {
      setLoading(true);
      try {
        const res = await fetch('http://localhost:8000/gmail/draft', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ thread_id: threadId, user_context: null })
        });

        if (!res.ok) throw new Error('Failed to load thread');

        const data = await res.json();
        setThread(data.thread);
        // Don't set draft yet - user hasn't provided context
      } catch (error) {
        alert('Failed to load conversation');
        console.error(error);
        onBack();
      } finally {
        setLoading(false);
      }
    }

    loadThread();
  }, [threadId, onBack]);

  const handleGenerateDraft = async () => {
    setGeneratingDraft(true);
    try {
      const res = await fetch('http://localhost:8000/gmail/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, user_context: userContext || null })
      });

      if (!res.ok) throw new Error('Failed to generate draft');

      const data = await res.json();
      setDraftBody(data.draft.body);
      setStep('review');
    } catch (error) {
      alert('Failed to generate draft');
      console.error(error);
    } finally {
      setGeneratingDraft(false);
    }
  };

  const handleSendEmail = async () => {
    if (!thread) return;
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/gmail/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: thread.thread_id,
          body: draftBody,
          to: thread.to,
          subject: thread.subject,
          message_id: thread.message_id,
          references: thread.references
        })
      });

      if (!res.ok) throw new Error('Failed to send email');

      setStep('sent');
    } catch (error) {
      alert('Failed to send email');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <div className="text-4xl mb-4">⏳</div>
        <p className="text-gray-600">Loading conversation...</p>
      </div>
    );
  }

  // STEP 1: Show Conversation + Context Input
  if (step === 'context' && thread) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <button onClick={onBack} className="mb-4 text-blue-600 hover:underline">
          ← Back to inbox
        </button>
        
        <h2 className="text-2xl font-bold mb-6">Email Conversation</h2>

        {/* Show the conversation */}
        <div className="mb-6 bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
          <h3 className="font-semibold mb-3">Thread History</h3>
          {thread.messages.map((msg, i) => (
            <div key={i} className="mb-4 pb-4 border-b last:border-b-0">
              <div className="text-sm font-medium text-gray-700">{msg.from}</div>
              <div className="text-xs text-gray-500 mb-2">{msg.date}</div>
              <div className="text-sm whitespace-pre-wrap">{msg.body}</div>
            </div>
          ))}
        </div>

        {/* Context input */}
        <div className="bg-white rounded-lg border p-6">
          <h3 className="font-semibold mb-2">Add Instructions (Optional)</h3>
          <p className="text-sm text-gray-600 mb-4">
            Tell the AI how to respond (e.g., "Keep it brief", "Decline politely", "Request more details")
          </p>
          
          <textarea
            className="w-full p-3 border rounded-lg mb-4 h-32"
            placeholder="Optional instructions for AI..."
            value={userContext}
            onChange={(e) => setUserContext(e.target.value)}
          />

          <button
            onClick={handleGenerateDraft}
            disabled={generatingDraft}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed w-full"
          >
            {generatingDraft ? 'Generating Reply...' : 'Generate AI Reply'}
          </button>
        </div>
      </div>
    );
  }

  // STEP 2: Review & Edit Draft
  if (step === 'review' && thread) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <h2 className="text-2xl font-bold mb-6">Review & Edit Draft</h2>

        {/* Conversation History (collapsed) */}
        <details className="mb-6 bg-gray-50 rounded-lg p-4">
          <summary className="font-semibold cursor-pointer">View Original Conversation</summary>
          <div className="mt-3 max-h-64 overflow-y-auto">
            {thread.messages.map((msg, i) => (
              <div key={i} className="mb-3 pb-3 border-b last:border-b-0">
                <div className="text-sm font-medium text-gray-700">{msg.from}</div>
                <div className="text-xs text-gray-500 mb-2">{msg.date}</div>
                <div className="text-sm whitespace-pre-wrap">{msg.body}</div>
              </div>
            ))}
          </div>
        </details>

        {/* Draft Editor */}
        <div className="mb-6">
          <h3 className="font-semibold mb-2">Your Reply</h3>
          <textarea
            className="w-full p-4 border rounded-lg h-64 font-mono text-sm"
            value={draftBody}
            onChange={(e) => setDraftBody(e.target.value)}
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={handleSendEmail}
            disabled={loading}
            className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 flex-1"
          >
            {loading ? 'Sending...' : 'Send Email'}
          </button>

          <button
            onClick={() => { setStep('context'); setDraftBody(''); }}
            className="border border-gray-300 px-6 py-3 rounded-lg hover:bg-gray-50"
          >
            Regenerate
          </button>

          <button
            onClick={onBack}
            className="border border-gray-300 px-6 py-3 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // STEP 3: Success
  if (step === 'sent') {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <div className="text-6xl mb-4">✅</div>
        <h2 className="text-2xl font-bold mb-2">Email Sent!</h2>
        <p className="text-gray-600 mb-6">Your reply has been sent successfully.</p>
        <button
          onClick={onBack}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
        >
          Back to Inbox
        </button>
      </div>
    );
  }

  return null;
}
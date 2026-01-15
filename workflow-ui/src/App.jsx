import { useState } from 'react';
import GmailThreadPicker from './components/GmailThreadPicker';
import SimpleGmailWorkflow from './components/SimpleGmailWorkflow';

export default function App() {
  const [selectedThreadId, setSelectedThreadId] = useState(null);

  if (selectedThreadId) {
    return (
      <SimpleGmailWorkflow 
        threadId={selectedThreadId}
        onBack={() => setSelectedThreadId(null)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">Gmail AI Assistant</h1>
        <GmailThreadPicker onSelectThread={(id) => setSelectedThreadId(id)} />
      </div>
    </div>
  );
}
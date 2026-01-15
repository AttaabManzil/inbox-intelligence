import { Routes, Route } from "react-router-dom";

import GmailDraftPage from "./pages/GmailDraftPage.tsx";
import GmailContextPage from "./pages/GmailContextPage.tsx";
import GmailDraftReviewPage from "./pages/GmailDraftReviewPage.tsx";

export default function App() {
  return (
    <Routes>
      <Route path="/gmail/draft" element={<GmailDraftPage />} />
      <Route path="/gmail/context/:workflowId" element={<GmailContextPage />} />
      <Route
        path="/gmail/draft/review/:workflowId"
        element={<GmailDraftReviewPage />}
      />
    </Routes>
  );
}

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import JobProfile from './pages/JobProfile';
import BulkScreening from './pages/BulkScreening';
import ManualReview from './pages/ManualReview';
import Verification from './pages/Verification';
import { FlowStateProvider } from './context/FlowStateContext';

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      {/* FlowStateProvider sits above <Routes> so Job Description / Shortlist
          Candidates keep their in-progress data when you navigate between them. */}
      <FlowStateProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="/job-profiles" element={<JobProfile />} />
            <Route path="/screening" element={<BulkScreening />} />
            <Route path="/manual-review" element={<ManualReview />} />
            <Route path="/verification" element={<Verification />} />
          </Route>
        </Routes>
      </FlowStateProvider>
    </BrowserRouter>
  );
}

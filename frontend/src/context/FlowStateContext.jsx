import { createContext, useContext, useState } from 'react';

const FlowStateContext = createContext(null);

const initialJobDraft = {
  jdFile: null,
  extractedPreview: null,
  extractError: null,
  title: '',
  department: '',
  minExp: '',
  maxExp: '',
  skills: [],
  eduDegree: '',
  eduField: '',
  eduMandatory: true,
  location: '',
  customRules: [],
};

const initialScreeningDraft = {
  zipFile: null,
  excelFile: null,
  processed: false,
  candidates: [],
  filter: 'All',
};

// This provider is mounted once in App.jsx, above <Routes>, so it survives
// navigating between pages (Job Description <-> Shortlist Candidates). Only a
// full page reload clears it — that's expected, same as any in-memory state.
export function FlowStateProvider({ children }) {
  const [jobDraft, setJobDraft] = useState(initialJobDraft);
  const [screeningDraft, setScreeningDraft] = useState(initialScreeningDraft);

  const updateJobDraft = (patch) => setJobDraft((prev) => ({ ...prev, ...patch }));
  const resetJobDraft = () => setJobDraft(initialJobDraft);

  const updateScreeningDraft = (patch) => setScreeningDraft((prev) => ({ ...prev, ...patch }));
  const resetScreeningDraft = () => setScreeningDraft(initialScreeningDraft);

  return (
    <FlowStateContext.Provider
      value={{
        jobDraft,
        updateJobDraft,
        resetJobDraft,
        screeningDraft,
        updateScreeningDraft,
        resetScreeningDraft,
      }}
    >
      {children}
    </FlowStateContext.Provider>
  );
}

export function useFlowState() {
  const ctx = useContext(FlowStateContext);
  if (!ctx) throw new Error('useFlowState must be used within a FlowStateProvider');
  return ctx;
}

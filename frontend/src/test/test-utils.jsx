import { render } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';

// Mock the auth API before AuthProvider tries to call it
vi.mock('../services/api', () => ({
  default: {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn().mockRejectedValue(new Error('no token')),
  },
  profileAPI: {
    get: vi.fn().mockResolvedValue({ data: {} }),
    update: vi.fn(),
  },
  applicationsAPI: {
    list: vi.fn().mockResolvedValue({ data: { applications: [], total: 0 } }),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    updateChecklistItem: vi.fn(),
  },
  essaysAPI: {
    list: vi.fn().mockResolvedValue({ data: { essays: [], total: 0 } }),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  documentsAPI: {
    list: vi.fn().mockResolvedValue({ data: { documents: [], total: 0 } }),
    get: vi.fn(),
    upload: vi.fn(),
    download: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  scholarshipsAPI: {
    list: vi.fn().mockResolvedValue({ data: { scholarships: [], total: 0 } }),
    get: vi.fn(),
  },
  llmAPI: {
    status: vi.fn().mockResolvedValue({ data: { available: false } }),
    getMatchExplanation: vi.fn(),
    parseScholarship: vi.fn(),
  },
  agentAPI: {
    status: vi.fn(),
    chat: vi.fn(),
    listSessions: vi.fn().mockResolvedValue({ data: [] }),
    getSession: vi.fn(),
    archiveSession: vi.fn(),
    getRecommendations: vi.fn(),
    quickSearch: vi.fn(),
    quickMatch: vi.fn(),
    quickChecklist: vi.fn(),
  },
  scraperAPI: {
    status: vi.fn(),
    sources: vi.fn(),
    startJob: vi.fn(),
    listJobs: vi.fn(),
    getJob: vi.fn(),
    cancelJob: vi.fn(),
    getLogs: vi.fn(),
    listConfigs: vi.fn(),
    getConfig: vi.fn(),
    updateConfig: vi.fn(),
  },
}));

export function renderWithRouter(ui, { route = '/' } = {}) {
  window.history.pushState({}, 'Test page', route);
  return render(ui, { wrapper: BrowserRouter });
}

export function renderWithAuth(ui, { route = '/' } = {}) {
  window.history.pushState({}, 'Test page', route);
  return render(ui, {
    wrapper: ({ children }) => (
      <BrowserRouter>
        <AuthProvider>{children}</AuthProvider>
      </BrowserRouter>
    ),
  });
}

export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { authAPI } from './services/api';
import App from './App';

vi.mock('./services/api', () => ({
  default: {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn(),
  },
  applicationsAPI: {
    list: vi.fn().mockResolvedValue({ data: { applications: [], total: 0 } }),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    updateChecklistItem: vi.fn(),
  },
  scholarshipsAPI: {
    list: vi.fn().mockResolvedValue({ data: { scholarships: [], total: 0 } }),
    get: vi.fn(),
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
  profileAPI: {
    get: vi.fn().mockResolvedValue({ data: {} }),
    update: vi.fn(),
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

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('redirects unauthenticated users to login', async () => {
    authAPI.me.mockRejectedValue(new Error('no token'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Sign in to ScholarAgent')).toBeInTheDocument();
    });
  });

  it('shows dashboard for authenticated users', async () => {
    localStorage.setItem('token', 'valid-token');
    authAPI.me.mockResolvedValue({
      data: { id: 1, email: 'test@test.com', is_admin: false },
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });
});

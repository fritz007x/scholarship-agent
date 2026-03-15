import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';
import { authAPI, applicationsAPI } from '../services/api';
import Dashboard from './Dashboard';

vi.mock('../services/api', () => ({
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn(),
  },
  applicationsAPI: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    updateChecklistItem: vi.fn(),
  },
}));

function renderDashboard() {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Dashboard />
      </AuthProvider>
    </BrowserRouter>
  );
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('token', 'test-token');
    authAPI.me.mockResolvedValue({
      data: { id: 1, email: 'test@test.com', is_admin: false },
    });
  });

  it('shows loading spinner initially', () => {
    applicationsAPI.list.mockReturnValue(new Promise(() => {}));
    renderDashboard();
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders dashboard title after loading', async () => {
    applicationsAPI.list.mockResolvedValue({
      data: { applications: [], total: 0 },
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });

  it('shows empty state when no applications', async () => {
    applicationsAPI.list.mockResolvedValue({
      data: { applications: [], total: 0 },
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("You haven't started any applications yet.")).toBeInTheDocument();
    });
    expect(screen.getByText('Browse Scholarships')).toBeInTheDocument();
  });

  it('displays stats cards', async () => {
    applicationsAPI.list.mockResolvedValue({
      data: {
        applications: [
          { id: 1, scholarship_name: 'Test', status: 'in_progress', checklist_total: 3, checklist_completed: 1 },
          { id: 2, scholarship_name: 'Other', status: 'submitted', checklist_total: 2, checklist_completed: 2 },
          { id: 3, scholarship_name: 'Won Prize', status: 'awarded', checklist_total: 2, checklist_completed: 2 },
        ],
        total: 3,
      },
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Total Applications')).toBeInTheDocument();
    });
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Submitted')).toBeInTheDocument();
    expect(screen.getByText('Awarded')).toBeInTheDocument();
  });

  it('displays application list with scholarship names', async () => {
    applicationsAPI.list.mockResolvedValue({
      data: {
        applications: [
          {
            id: 1,
            scholarship_name: 'STEM Award',
            scholarship_provider: 'Tech Foundation',
            scholarship_award_amount: 5000,
            status: 'in_progress',
            checklist_total: 4,
            checklist_completed: 2,
          },
        ],
        total: 1,
      },
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('STEM Award')).toBeInTheDocument();
    });
    expect(screen.getByText('Tech Foundation')).toBeInTheDocument();
    expect(screen.getByText('$5,000')).toBeInTheDocument();
    expect(screen.getByText('2/4 complete')).toBeInTheDocument();
  });

  it('shows error when API fails', async () => {
    applicationsAPI.list.mockRejectedValue(new Error('Network error'));

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Failed to load applications')).toBeInTheDocument();
    });
  });

  it('links to scholarship search page', async () => {
    applicationsAPI.list.mockResolvedValue({
      data: { applications: [], total: 0 },
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Find Scholarships')).toBeInTheDocument();
    });
    expect(screen.getByText('Find Scholarships').closest('a')).toHaveAttribute('href', '/scholarships');
  });
});

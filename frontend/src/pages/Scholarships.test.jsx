import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';
import { authAPI, scholarshipsAPI, llmAPI, applicationsAPI } from '../services/api';
import Scholarships from './Scholarships';

vi.mock('../services/api', () => ({
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn(),
  },
  scholarshipsAPI: {
    list: vi.fn(),
    get: vi.fn(),
  },
  applicationsAPI: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    updateChecklistItem: vi.fn(),
  },
  llmAPI: {
    status: vi.fn(),
    getMatchExplanation: vi.fn(),
    parseScholarship: vi.fn(),
  },
}));

function renderScholarships() {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Scholarships />
      </AuthProvider>
    </BrowserRouter>
  );
}

describe('Scholarships', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('token', 'test-token');
    authAPI.me.mockResolvedValue({
      data: { id: 1, email: 'test@test.com', is_admin: false },
    });
    llmAPI.status.mockResolvedValue({ data: { available: false } });
  });

  it('renders page title', async () => {
    scholarshipsAPI.list.mockResolvedValue({
      data: { scholarships: [], total: 0 },
    });

    renderScholarships();

    await waitFor(() => {
      expect(screen.getByText('Find Scholarships')).toBeInTheDocument();
    });
  });

  it('shows empty state when no scholarships', async () => {
    scholarshipsAPI.list.mockResolvedValue({
      data: { scholarships: [], total: 0 },
    });

    renderScholarships();

    await waitFor(() => {
      expect(screen.getByText('No scholarships available.')).toBeInTheDocument();
    });
  });

  it('displays scholarship cards', async () => {
    scholarshipsAPI.list.mockResolvedValue({
      data: {
        scholarships: [
          {
            id: 1,
            name: 'STEM Excellence',
            provider: 'Tech Foundation',
            description: 'For STEM students',
            award_amount: 5000,
            deadline: '2026-12-31',
          },
        ],
        total: 1,
      },
    });

    renderScholarships();

    await waitFor(() => {
      expect(screen.getByText('STEM Excellence')).toBeInTheDocument();
    });
    expect(screen.getByText('Tech Foundation')).toBeInTheDocument();
    expect(screen.getByText('For STEM students')).toBeInTheDocument();
    expect(screen.getByText('$5,000')).toBeInTheDocument();
  });

  it('searches scholarships on form submit', async () => {
    const user = userEvent.setup();
    scholarshipsAPI.list
      .mockResolvedValueOnce({ data: { scholarships: [], total: 0 } })
      .mockResolvedValueOnce({
        data: {
          scholarships: [{ id: 1, name: 'Found Scholarship', award_amount: 1000 }],
          total: 1,
        },
      });

    renderScholarships();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search scholarships/)).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText(/Search scholarships/), 'engineering');
    await user.click(screen.getByRole('button', { name: /Search/ }));

    await waitFor(() => {
      expect(scholarshipsAPI.list).toHaveBeenCalledWith({ search: 'engineering' });
    });
  });

  it('shows AI match badge when LLM is available', async () => {
    llmAPI.status.mockResolvedValue({ data: { available: true } });
    scholarshipsAPI.list.mockResolvedValue({
      data: { scholarships: [], total: 0 },
    });

    renderScholarships();

    await waitFor(() => {
      expect(screen.getByText('AI Match Analysis Available')).toBeInTheDocument();
    });
  });

  it('shows no match search message', async () => {
    scholarshipsAPI.list.mockResolvedValue({
      data: { scholarships: [], total: 0 },
    });

    renderScholarships();

    // Type something in search first so the empty message changes
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search scholarships/)).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText(/Search scholarships/), 'xyz');
    await user.click(screen.getByRole('button', { name: /Search/ }));

    scholarshipsAPI.list.mockResolvedValue({
      data: { scholarships: [], total: 0 },
    });

    await waitFor(() => {
      expect(screen.getByText('No scholarships found matching your search.')).toBeInTheDocument();
    });
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';
import { authAPI, essaysAPI } from '../services/api';
import Essays from './Essays';

vi.mock('../services/api', () => ({
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn(),
  },
  essaysAPI: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

function renderEssays() {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Essays />
      </AuthProvider>
    </BrowserRouter>
  );
}

describe('Essays', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('token', 'test-token');
    authAPI.me.mockResolvedValue({
      data: { id: 1, email: 'test@test.com', is_admin: false },
    });
  });

  it('renders page title', async () => {
    essaysAPI.list.mockResolvedValue({ data: { essays: [], total: 0 } });

    renderEssays();

    await waitFor(() => {
      expect(screen.getByText('Essay Library')).toBeInTheDocument();
    });
  });

  it('shows empty state when no essays', async () => {
    essaysAPI.list.mockResolvedValue({ data: { essays: [], total: 0 } });

    renderEssays();

    await waitFor(() => {
      expect(screen.getByText(/No essays yet/)).toBeInTheDocument();
    });
    expect(screen.getByText('Create Your First Essay')).toBeInTheDocument();
  });

  it('displays essay cards', async () => {
    essaysAPI.list.mockResolvedValue({
      data: {
        essays: [
          {
            id: 1,
            title: 'Leadership Essay',
            content: 'I have demonstrated leadership through various activities',
            prompt_category: 'leadership',
            used_in_applications: [1],
            word_count: 7,
          },
        ],
        total: 1,
      },
    });

    renderEssays();

    await waitFor(() => {
      expect(screen.getByText('Leadership Essay')).toBeInTheDocument();
    });
    expect(screen.getByText('Used in 1 applications')).toBeInTheDocument();
  });

  it('opens editor when creating new essay', async () => {
    const user = userEvent.setup();
    essaysAPI.list.mockResolvedValue({ data: { essays: [], total: 0 } });
    essaysAPI.create.mockResolvedValue({
      data: {
        id: 1,
        title: 'New Essay',
        content: '',
        prompt: '',
        prompt_category: 'other',
      },
    });

    renderEssays();

    await waitFor(() => {
      expect(screen.getByText('Essay Library')).toBeInTheDocument();
    });

    // The top button has icon + "New Essay" text
    const buttons = screen.getAllByRole('button');
    const newEssayBtn = buttons.find(btn => btn.textContent.includes('New Essay'));
    await user.click(newEssayBtn);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Essay Title')).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText('Write your essay...')).toBeInTheDocument();
    expect(screen.getByText('Save Essay')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });
});

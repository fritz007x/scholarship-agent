import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../contexts/AuthContext';
import { authAPI } from '../../services/api';
import Layout from './Layout';

vi.mock('../../services/api', () => ({
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn(),
  },
}));

function renderLayout(children = <div>Content</div>) {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Layout>{children}</Layout>
      </AuthProvider>
    </BrowserRouter>
  );
}

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('token', 'test-token');
    authAPI.me.mockResolvedValue({
      data: { id: 1, email: 'user@test.com', is_admin: false },
    });
  });

  it('renders children content', async () => {
    renderLayout(<div>My Page</div>);

    expect(screen.getByText('My Page')).toBeInTheDocument();
  });

  it('shows navigation links', async () => {
    renderLayout();

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.getByText('Scholarships')).toBeInTheDocument();
    expect(screen.getByText('Essays')).toBeInTheDocument();
    expect(screen.getByText('Documents')).toBeInTheDocument();
  });

  it('shows app name', () => {
    renderLayout();
    expect(screen.getByText('ScholarAgent')).toBeInTheDocument();
  });

  it('does not show admin section for regular users', async () => {
    renderLayout();
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
    expect(screen.queryByText('Scraper Admin')).not.toBeInTheDocument();
  });

  it('shows admin section for admin users', async () => {
    authAPI.me.mockResolvedValue({
      data: { id: 1, email: 'admin@test.com', is_admin: true },
    });

    renderLayout();

    // Wait for auth to resolve
    await vi.waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });
    expect(screen.getByText('Scraper Admin')).toBeInTheDocument();
  });

  it('shows user email', async () => {
    renderLayout();

    await vi.waitFor(() => {
      expect(screen.getByText('user@test.com')).toBeInTheDocument();
    });
  });

  it('has a logout button', async () => {
    renderLayout();

    await vi.waitFor(() => {
      expect(screen.getByTitle('Logout')).toBeInTheDocument();
    });
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';
import { authAPI } from '../services/api';
import Login from './Login';

vi.mock('../services/api', () => ({
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn().mockRejectedValue(new Error('no token')),
  },
}));

function renderLogin() {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </BrowserRouter>
  );
}

function getInput(label) {
  return screen.getByText(label).closest('div').querySelector('input');
}

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    authAPI.me.mockRejectedValue(new Error('no token'));
  });

  it('renders login form', async () => {
    renderLogin();

    await waitFor(() => {
      expect(screen.getByText('Sign in to ScholarAgent')).toBeInTheDocument();
    });
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('has link to register page', async () => {
    renderLogin();

    await waitFor(() => {
      expect(screen.getByText('Register')).toBeInTheDocument();
    });
    expect(screen.getByText('Register').closest('a')).toHaveAttribute('href', '/register');
  });

  it('shows validation error for empty submission', async () => {
    const user = userEvent.setup();
    renderLogin();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(screen.getByText('Invalid email address')).toBeInTheDocument();
    });
  });

  it('shows validation error for empty password', async () => {
    const user = userEvent.setup();
    renderLogin();

    await waitFor(() => {
      expect(getInput('Email')).toBeInTheDocument();
    });

    await user.type(getInput('Email'), 'test@test.com');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(screen.getByText('Password is required')).toBeInTheDocument();
    });
  });

  it('shows server error on failed login', async () => {
    const user = userEvent.setup();
    authAPI.login.mockRejectedValue({
      response: { data: { detail: 'Invalid email or password' } },
    });

    renderLogin();

    await waitFor(() => {
      expect(getInput('Email')).toBeInTheDocument();
    });

    await user.type(getInput('Email'), 'test@test.com');
    await user.type(getInput('Password'), 'WrongPass123');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(screen.getByText('Invalid email or password')).toBeInTheDocument();
    });
  });
});

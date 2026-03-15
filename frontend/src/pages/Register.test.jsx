import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';
import { authAPI } from '../services/api';
import Register from './Register';

vi.mock('../services/api', () => ({
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn().mockRejectedValue(new Error('no token')),
  },
}));

function renderRegister() {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Register />
      </AuthProvider>
    </BrowserRouter>
  );
}

function getInput(label) {
  return screen.getByText(label).closest('div').querySelector('input');
}

describe('Register', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    authAPI.me.mockRejectedValue(new Error('no token'));
  });

  it('renders registration form', async () => {
    renderRegister();

    await waitFor(() => {
      expect(screen.getByText('Create your account')).toBeInTheDocument();
    });
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByText('Password')).toBeInTheDocument();
    expect(screen.getByText('Confirm Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create account' })).toBeInTheDocument();
  });

  it('has link to login page', async () => {
    renderRegister();

    await waitFor(() => {
      expect(screen.getByText('Sign in')).toBeInTheDocument();
    });
    expect(screen.getByText('Sign in').closest('a')).toHaveAttribute('href', '/login');
  });

  it('validates password minimum length', async () => {
    const user = userEvent.setup();
    renderRegister();

    await waitFor(() => {
      expect(getInput('Email')).toBeInTheDocument();
    });

    await user.type(getInput('Email'), 'test@test.com');
    await user.type(getInput('Password'), 'Short1');
    await user.type(getInput('Confirm Password'), 'Short1');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() => {
      expect(screen.getByText('Password must be at least 8 characters')).toBeInTheDocument();
    });
  });

  it('validates password requires uppercase', async () => {
    const user = userEvent.setup();
    renderRegister();

    await waitFor(() => {
      expect(getInput('Email')).toBeInTheDocument();
    });

    await user.type(getInput('Email'), 'test@test.com');
    await user.type(getInput('Password'), 'alllower1');
    await user.type(getInput('Confirm Password'), 'alllower1');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() => {
      expect(screen.getByText('Password must contain at least one uppercase letter')).toBeInTheDocument();
    });
  });

  it('validates password requires digit', async () => {
    const user = userEvent.setup();
    renderRegister();

    await waitFor(() => {
      expect(getInput('Email')).toBeInTheDocument();
    });

    await user.type(getInput('Email'), 'test@test.com');
    await user.type(getInput('Password'), 'NoDigitsHere');
    await user.type(getInput('Confirm Password'), 'NoDigitsHere');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() => {
      expect(screen.getByText('Password must contain at least one digit')).toBeInTheDocument();
    });
  });

  it('validates passwords must match', async () => {
    const user = userEvent.setup();
    renderRegister();

    await waitFor(() => {
      expect(getInput('Email')).toBeInTheDocument();
    });

    await user.type(getInput('Email'), 'test@test.com');
    await user.type(getInput('Password'), 'ValidPass1');
    await user.type(getInput('Confirm Password'), 'DiffPass1');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() => {
      expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
    });
  });

  it('shows server error on failed registration', async () => {
    const user = userEvent.setup();
    authAPI.register.mockRejectedValue({
      response: { data: { detail: 'Email already registered' } },
    });

    renderRegister();

    await waitFor(() => {
      expect(getInput('Email')).toBeInTheDocument();
    });

    await user.type(getInput('Email'), 'existing@test.com');
    await user.type(getInput('Password'), 'ValidPass1');
    await user.type(getInput('Confirm Password'), 'ValidPass1');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() => {
      expect(screen.getByText('Email already registered')).toBeInTheDocument();
    });
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from './AuthContext';
import { authAPI } from '../services/api';

vi.mock('../services/api', () => ({
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn(),
  },
}));

function TestConsumer() {
  const { user, isAuthenticated, isAdmin, loading, login, logout, register } = useAuth();

  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="admin">{String(isAdmin)}</span>
      <span data-testid="email">{user?.email || 'none'}</span>
      <button onClick={() => login('test@test.com', 'Pass123')} data-testid="login-btn">Login</button>
      <button onClick={logout} data-testid="logout-btn">Logout</button>
      <button onClick={() => register('new@test.com', 'Pass123')} data-testid="register-btn">Register</button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('starts unauthenticated when no token', async () => {
    authAPI.me.mockRejectedValue(new Error('no token'));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('email')).toHaveTextContent('none');
  });

  it('restores user from token on mount', async () => {
    localStorage.setItem('token', 'valid-token');
    authAPI.me.mockResolvedValue({
      data: { id: 1, email: 'existing@test.com', is_admin: false },
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });
    expect(screen.getByTestId('email')).toHaveTextContent('existing@test.com');
  });

  it('login stores token and sets user', async () => {
    const user = userEvent.setup();

    // No token in localStorage, so checkAuth won't call me()
    // me() will only be called inside the login flow
    authAPI.me.mockResolvedValue({
      data: { id: 1, email: 'test@test.com', is_admin: false },
    });

    authAPI.login.mockResolvedValue({
      data: { access_token: 'new-token', token_type: 'bearer' },
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    await user.click(screen.getByTestId('login-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });
    expect(localStorage.getItem('token')).toBe('new-token');
    expect(screen.getByTestId('email')).toHaveTextContent('test@test.com');
  });

  it('logout clears user and token', async () => {
    const user = userEvent.setup();
    localStorage.setItem('token', 'some-token');
    authAPI.me.mockResolvedValue({
      data: { id: 1, email: 'test@test.com', is_admin: false },
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });

    await user.click(screen.getByTestId('logout-btn'));

    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    expect(localStorage.getItem('token')).toBeNull();
  });

  it('detects admin user', async () => {
    localStorage.setItem('token', 'admin-token');
    authAPI.me.mockResolvedValue({
      data: { id: 1, email: 'admin@test.com', is_admin: true },
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('admin')).toHaveTextContent('true');
    });
  });

  it('clears token on failed auth check', async () => {
    localStorage.setItem('token', 'expired-token');
    authAPI.me.mockRejectedValue(new Error('401'));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });
    expect(localStorage.getItem('token')).toBeNull();
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
  });

  it('throws when useAuth is used outside AuthProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow(
      'useAuth must be used within an AuthProvider'
    );
    consoleSpy.mockRestore();
  });
});

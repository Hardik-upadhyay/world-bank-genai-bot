/**
 * Auth Service – manages JWT tokens and user session
 */

const TOKEN_KEY = 'wb_token';
const USER_KEY  = 'wb_user';

export const login = async (username, password) => {
  const res = await fetch('http://localhost:8000/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed. Check your credentials.');
  }

  const data = await res.json();
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify({
    userId: data.user_id,
    role: data.role,
    fullName: data.full_name,
  }));
  return data;
};

export const logout = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const getToken = () => localStorage.getItem(TOKEN_KEY);

export const getCurrentUser = () => {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export const isAuthenticated = () => !!getToken();

export const isManager = () => {
  const user = getCurrentUser();
  return user?.role === 'manager';
};

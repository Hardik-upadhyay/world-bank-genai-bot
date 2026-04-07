import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../services/auth';

const Login = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await login(username.trim().toLowerCase(), password);
      if (data.role === 'manager') navigate('/manager');
      else navigate('/chat');
    } catch (err) {
      setError(err.message || 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-layout">
      {/* Background grid */}
      <div className="login-bg-grid" />

      <div className="login-card">
        {/* Logo */}
        <div className="login-logo">
          <div className="login-logo__icon">🏛️</div>
          <div>
            <div className="login-logo__title">The World Bank</div>
            <div className="login-logo__subtitle">AI Banking Assistant</div>
          </div>
        </div>

        <p className="login-tagline">Secure. Intelligent. For everyone.</p>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label className="login-label">Username</label>
            <input
              id="login-username"
              type="text"
              className="login-input"
              placeholder="Enter your username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoComplete="username"
            />
          </div>
          <div className="login-field">
            <label className="login-label">Password</label>
            <input
              id="login-password"
              type="password"
              className="login-input"
              placeholder="Enter your password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          {error && <div className="login-error">⚠️ {error}</div>}

          <button id="login-submit" type="submit" className="login-btn" disabled={loading}>
            {loading ? <span className="login-btn__spinner" /> : 'Sign In'}
          </button>
        </form>

        <div className="login-demo-hint">
          <p>Demo accounts:</p>
          <code>manager / manager123</code><br/>
          <code>alice / alice123 &nbsp;•&nbsp; rahul / rahul123 &nbsp;•&nbsp; sofia / sofia123</code>
        </div>

        <button className="login-back-btn" onClick={() => navigate('/')}>
          ← Back to Home
        </button>
      </div>
    </div>
  );
};

export default Login;

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { askBankingFAQ } from '../services/api';

const FEATURES = [
  { icon: '🏦', title: 'Savings & Accounts', desc: 'Competitive interest rates, zero-balance options, and digital-first banking.' },
  { icon: '🏠', title: 'Home Loans', desc: 'Lowest rates, up to 30-year tenure, pre-approval in 24 hours.' },
  { icon: '💳', title: 'Cards & Credit', desc: 'Reward points, lounge access, travel insurance and zero fraud liability.' },
  { icon: '📈', title: 'Investments', desc: 'Mutual funds, SIPs, FDs, PPF — all from one secure platform.' },
  { icon: '🌍', title: 'Global Banking', desc: 'Multi-currency FCNR accounts, SWIFT transfers, Forex cards.' },
  { icon: '🔒', title: 'Secure & Trusted', desc: 'RBI-regulated, 2FA, real-time alerts, zero-liability fraud policy.' },
];

const QUICK_QUESTIONS = [
  'What are the savings account interest rates?',
  'How do I apply for a home loan?',
  'What documents are needed for KYC?',
  'What are the NEFT transfer limits?',
];

const WELCOME = {
  id: 'welcome',
  role: 'assistant',
  content: `👋 Welcome to **The World Bank** AI Assistant!\n\nI can answer general banking questions about:\n• Interest rates & account types\n• Loan eligibility & documents\n• Cards, transfers & digital banking\n• KYC, compliance & investments\n\nFor personal account details, please **log in** first. How can I help?`,
  isPersonal: false,
};

let msgId = 1;

// ── Compact chat bubble (no avatar) for landing page ─────────────────────────
const LandingMessage = ({ msg }) => {
  const isUser = msg.role === 'user';
  return (
    <div className={`lp-bubble-row ${isUser ? 'lp-bubble-row--user' : 'lp-bubble-row--bot'}`}>
      {!isUser && <span className="lp-bot-icon">🏦</span>}
      <div className={`lp-bubble ${isUser ? 'lp-bubble--user' : 'lp-bubble--bot'} ${msg.isPersonal ? 'lp-bubble--locked' : ''}`}>
        {isUser ? (
          <span>{msg.content}</span>
        ) : (
          <div className="markdown-body lp-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
      {isUser && <span className="lp-user-icon">👤</span>}
    </div>
  );
};

// ── Landing Page ──────────────────────────────────────────────────────────────
const Landing = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatMessagesRef = useRef(null);
  const inputRef = useRef(null);
  const [chatOpen, setChatOpen] = useState(false);

  // Only auto-scroll the chat box, never the whole page
  useEffect(() => {
    if (!chatOpen) return;
    const container = chatMessagesRef.current;
    if (container) container.scrollTop = container.scrollHeight;
  }, [messages, loading, chatOpen]);

  const buildHistory = (msgs) =>
    msgs.filter(m => m.id !== 'welcome').map(m => ({ role: m.role, content: m.content }));

  const handleSend = useCallback(async (text) => {
    const q = (text || input).trim();
    if (!q || loading) return;
    setInput('');
    setChatOpen(true);

    const userMsg = { id: `u-${++msgId}`, role: 'user', content: q };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const history = buildHistory([...messages, userMsg]);
      const data = await askBankingFAQ(q, history.slice(0, -1));
      setMessages(prev => [...prev, {
        id: `a-${++msgId}`,
        role: 'assistant',
        content: data.answer,
        isPersonal: data.query_type === 'personal_guest',
        modelUsed: data.model_used,
        ragContextFound: data.rag_context_found,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        id: `e-${++msgId}`,
        role: 'assistant',
        content: 'I\'m temporarily unavailable. Please try again or call **1800-XXX-XXXX**.',
        isPersonal: false,
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [input, loading, messages]);

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div className="lp-root">
      {/* ── Background grid ── */}
      <div className="lp-grid-bg" />

      {/* ── Navbar ── */}
      <nav className="lp-nav">
        <div className="lp-nav-brand">
          <span className="lp-nav-icon">🏛️</span>
          <div>
            <span className="lp-nav-title">The World Bank</span>
            <span className="lp-nav-tag">AI Banking Assistant</span>
          </div>
        </div>
        <div className="lp-nav-actions">
          <span className="status-badge">
            <span className="status-badge__dot" />
            Online 24/7
          </span>
          <button id="lp-login-btn" className="lp-btn lp-btn--outline" onClick={() => navigate('/login')}>
            Sign In
          </button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="lp-hero">
        <div className="lp-hero-content">
          <div className="lp-hero-badge">✦ Powered by RAG + GenAI</div>
          <h1 className="lp-hero-title">
            Banking That<br />
            <span className="lp-hero-accent">Works for You</span>
          </h1>
          <p className="lp-hero-sub">
            AI-powered assistance, real-time answers, and world-class financial products —
            all in one secure, intelligent platform.
          </p>
          <div className="lp-hero-cta">
            <button className="lp-btn lp-btn--primary" onClick={() => navigate('/login')}>
              🚀 Get Started
            </button>
            <button className="lp-btn lp-btn--ghost" onClick={() => { setChatOpen(true); inputRef.current?.focus(); }}>
              💬 Ask AI Assistant
            </button>
          </div>
          <div className="lp-hero-stats">
            <div className="lp-stat"><span className="lp-stat-num">₹5Cr+</span><span className="lp-stat-label">Max Home Loan</span></div>
            <div className="lp-stat-divider" />
            <div className="lp-stat"><span className="lp-stat-num">4.25%</span><span className="lp-stat-label">Savings Rate</span></div>
            <div className="lp-stat-divider" />
            <div className="lp-stat"><span className="lp-stat-num">24/7</span><span className="lp-stat-label">AI Support</span></div>
          </div>
        </div>

        {/* ── Embedded Chatbot ── */}
        <div className={`lp-chat-card ${chatOpen ? 'lp-chat-card--open' : ''}`}>
          <div className="lp-chat-header">
            <div className="lp-chat-header-left">
              <span className="lp-chat-icon">🤖</span>
              <div>
                <p className="lp-chat-title">AI Banking Assistant</p>
                <p className="lp-chat-sub">Ask any banking question</p>
              </div>
            </div>
            <button className="lp-login-hint" onClick={() => navigate('/login')}>
              🔐 Login for personal info
            </button>
          </div>

          <div className="lp-chat-messages" ref={chatMessagesRef}>
            {!chatOpen && (
              <div className="lp-quick-chips">
                {QUICK_QUESTIONS.map((q, i) => (
                  <button key={i} className="lp-chip" onClick={() => handleSend(q)} disabled={loading}>
                    {q}
                  </button>
                ))}
              </div>
            )}
            {chatOpen && messages.map(msg => <LandingMessage key={msg.id} msg={msg} />)}
            {loading && (
              <div className="lp-bubble-row lp-bubble-row--bot">
                <span className="lp-bot-icon">🏦</span>
                <div className="lp-bubble lp-bubble--bot">
                  <span className="lp-typing"><span/><span/><span/></span>
                </div>
              </div>
            )}
          </div>

          <div className="lp-chat-input-bar">
            <input
              ref={inputRef}
              id="lp-chat-input"
              className="lp-chat-input"
              placeholder="Ask about rates, loans, cards…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              disabled={loading}
            />
            <button
              id="lp-chat-send"
              className="lp-send-btn"
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
            >
              {loading ? <span className="lp-send-spinner" /> : '↑'}
            </button>
          </div>

          {chatOpen && (
            <button className="lp-reset-btn" onClick={() => { setMessages([WELCOME]); setChatOpen(false); }}>
              ↩ Start over
            </button>
          )}
        </div>
      </section>

      {/* ── Features ── */}
      <section className="lp-features">
        <h2 className="lp-features-title">Everything You Need, All in One Place</h2>
        <div className="lp-features-grid">
          {FEATURES.map((f, i) => (
            <div key={i} className="lp-feature-card">
              <span className="lp-feature-icon">{f.icon}</span>
              <h3 className="lp-feature-name">{f.title}</h3>
              <p className="lp-feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer CTA ── */}
      <section className="lp-footer-cta">
        <h2 className="lp-footer-cta-title">Ready to get started?</h2>
        <p className="lp-footer-cta-sub">Join millions of customers banking smarter with AI.</p>
        <button className="lp-btn lp-btn--primary lp-btn--lg" onClick={() => navigate('/login')}>
          Sign In to Your Account →
        </button>
      </section>

      <footer className="lp-footer">
        <span>© 2026 The World Bank · AI Banking Assistant · Secured by JWT + HTTPS</span>
      </footer>
    </div>
  );
};

export default Landing;

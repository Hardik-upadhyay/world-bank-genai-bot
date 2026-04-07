import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { pdf } from '@react-pdf/renderer';
import ChatMessage from '../components/ChatMessage';
import SourceCitations from '../components/SourceCitations';
import ThinkingIndicator from '../components/ThinkingIndicator';
import ChatPdfDocument from '../components/ChatPdfDocument';
import {
  askBankingFAQ, askWithFile, getCustomerDashboard,
  createChatSession, updateChatSession, listChatSessions, getChatSession, deleteChatSession
} from '../services/api';
import { logout, getCurrentUser } from '../services/auth';

const QUICK_QUESTIONS = [
  "What is the interest rate for a savings account?",
  "How do I apply for a home loan?",
  "What documents do I need for KYC?",
  "How to report a lost credit card?",
  "What are the NEFT transfer limits?",
  "How is CIBIL score calculated?",
];

const WELCOME_MESSAGE = {
  id: 'welcome',
  role: 'assistant',
  content: `Welcome! I'm your AI Banking Assistant. 🏦

I can help you with:
• Account information & balances
• Loan eligibility & interest rates
• Credit & debit card queries
• Fund transfers & transaction details
• KYC, compliance & documentation
• Investment & insurance products

📎 **New:** You can also attach a screenshot or PDF to verify a bank message, summarise a statement, or ask questions about a document.

How can I assist you today?`,
  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  sources: [],
  modelUsed: null,
  ragContextFound: null,
};

let messageIdCounter = 1;

// ── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (n, currency = 'USD') => {
  const num = parseFloat(n) || 0;
  const curr = (currency || 'USD').toUpperCase();
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: curr,
    maximumFractionDigits: 2,
  }).format(num);
};

const maskAccount = (num) => {
  if (!num) return '—';
  return num.slice(0, 2) + ' •••• •••• ' + num.slice(-4);
};

const kycColor = (status) =>
  status === 'verified' ? '#22c55e' : status === 'pending' ? '#f59e0b' : '#ef4444';

const txIcon = (type) => (type === 'credit' ? '↑' : '↓');
const txColor = (type) => (type === 'credit' ? '#22c55e' : '#f87171');

// ── Account Card ──────────────────────────────────────────────────────────────

const AccountCard = ({ account }) => (
  <div className="db-account-card">
    <div className="db-account-header">
      <span className="db-account-type">{account.account_type}</span>
      <span className="db-account-status">{account.status}</span>
    </div>
    <div className="db-account-number">{maskAccount(account.account_number)}</div>
    <div className="db-account-balance">
      <span className="db-balance-label">Available Balance</span>
      <span className="db-balance-amount">{fmt(account.balance, account.currency)}</span>
    </div>
    <div className="db-account-meta">
      <span>📍 {account.branch || 'HQ'}</span>
      {account.opened_date && (
        <span>📅 Since {new Date(account.opened_date).toLocaleDateString('en-IN', { year: 'numeric', month: 'short' })}</span>
      )}
    </div>
  </div>
);

// ── Dashboard Panel ───────────────────────────────────────────────────────────

const DashboardPanel = ({ dashboard, loading, onRefresh }) => {
  if (loading) {
    return (
      <div className="db-panel">
        <div className="db-loading">
          <span className="db-spinner" />
          <span>Loading your account…</span>
        </div>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="db-panel">
        <div className="db-error">
          <span>⚠️ Could not load dashboard.</span>
          <button className="db-refresh-btn" onClick={onRefresh}>Retry</button>
        </div>
      </div>
    );
  }

  const { user, accounts, recent_transactions } = dashboard;
  // Use the currency of the first account, or fallback to USD
  const baseCurrency = accounts[0]?.currency || 'USD';
  const totalBalance = accounts.reduce((s, a) => s + (parseFloat(a.balance) || 0), 0);

  return (
    <aside className="db-panel">
      {/* Profile */}
      <div className="db-profile">
        <div className="db-avatar">{user.full_name?.charAt(0).toUpperCase()}</div>
        <div className="db-profile-info">
          <h2 className="db-name">{user.full_name}</h2>
          <span className="db-cid">{user.customer_id || 'Customer'}</span>
          <span
            className="db-kyc-badge"
            style={{ background: kycColor(user.kyc_status) + '22', color: kycColor(user.kyc_status), borderColor: kycColor(user.kyc_status) + '44' }}
          >
            KYC {user.kyc_status || 'N/A'}
          </span>
        </div>
        <button className="db-refresh-btn" onClick={onRefresh} title="Refresh dashboard">⟳</button>
      </div>

      {/* Total balance summary */}
      <div className="db-total-balance">
        <span className="db-total-label">Total Portfolio Value</span>
        <span className="db-total-amount">{fmt(totalBalance, baseCurrency)}</span>
        <span className="db-total-sub">{accounts.length} account{accounts.length !== 1 ? 's' : ''} · {baseCurrency}</span>
      </div>

      {/* Accounts */}
      <div className="db-section">
        <h3 className="db-section-title">My Accounts</h3>
        {accounts.length === 0 ? (
          <p className="db-empty">No accounts found.</p>
        ) : (
          <div className="db-accounts-list">
            {accounts.map((acc) => (
              <AccountCard key={acc.account_number} account={acc} />
            ))}
          </div>
        )}
      </div>

      {/* Recent Transactions */}
      <div className="db-section">
        <h3 className="db-section-title">Recent Transactions</h3>
        {recent_transactions.length === 0 ? (
          <p className="db-empty">No recent transactions.</p>
        ) : (
          <div className="db-tx-list">
            {recent_transactions.map((tx) => (
              <div key={tx.id} className="db-tx-row">
                <span className="db-tx-icon" style={{ color: txColor(tx.transaction_type) }}>
                  {txIcon(tx.transaction_type)}
                </span>
                <div className="db-tx-info">
                  <span className="db-tx-desc">{tx.description || 'Transaction'}</span>
                  <span className="db-tx-date">{tx.date ? new Date(tx.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : ''} · {tx.account_type}</span>
                </div>
                <span className="db-tx-amount" style={{ color: txColor(tx.transaction_type) }}>
                  {tx.transaction_type === 'credit' ? '+' : '-'}
                  {fmt(Math.abs(tx.amount), tx.currency || baseCurrency)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Contact info */}
      {(user.email || user.phone) && (
        <div className="db-contact">
          {user.email && <span>✉️ {user.email}</span>}
          {user.phone && <span>📞 {user.phone}</span>}
        </div>
      )}
    </aside>
  );
};

// ── Main Home Component ───────────────────────────────────────────────────────

const Home = () => {
  const navigate = useNavigate();
  const currentUser = getCurrentUser();

  // Chatbot state
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [visibleSources, setVisibleSources] = useState({});
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  // File attachment state
  const [attachedFile, setAttachedFile] = useState(null);  // File object
  const [attachPreview, setAttachPreview] = useState(null); // { name, isImage, objectUrl? }

  // Chat History state
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);

  // Dashboard state
  const [dashboard, setDashboard] = useState(null);
  const [dashLoading, setDashLoading] = useState(true);

  // Mobile tab state (dashboard | chat)
  const [activeTab, setActiveTab] = useState('chat');

  const handleLogout = () => { logout(); navigate('/'); };

  // Fetch dashboard
  const fetchDashboard = useCallback(async () => {
    setDashLoading(true);
    try {
      const data = await getCustomerDashboard();
      setDashboard(data);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setDashboard(null);
    } finally {
      setDashLoading(false);
    }
  }, []);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  // Fetch session list on mount + when history panel opens
  const fetchSessions = useCallback(async () => {
    try {
      const data = await listChatSessions();
      setSessions(data.sessions || []);
    } catch { /* silently fail */ }
  }, []);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const toggleSources = useCallback((messageId) => {
    setVisibleSources(prev => ({ ...prev, [messageId]: !prev[messageId] }));
  }, []);

  const buildHistory = (msgs) =>
    msgs
      .filter(m => m.id !== 'welcome')
      .map(m => ({ role: m.role, content: m.content }));

  // File attachment helpers
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const isImage = file.type.startsWith('image/');
    const isPdf = file.type === 'application/pdf';
    if (!isImage && !isPdf) {
      toast.error('Only images (JPEG/PNG/WEBP) and PDFs are supported.', { duration: 3000 });
      return;
    }
    const preview = {
      name: file.name,
      isImage,
      objectUrl: isImage ? URL.createObjectURL(file) : null,
    };
    setAttachedFile(file);
    setAttachPreview(preview);
    // reset file input so the same file can be re-selected
    e.target.value = '';
  };

  const clearAttachment = () => {
    if (attachPreview?.objectUrl) URL.revokeObjectURL(attachPreview.objectUrl);
    setAttachedFile(null);
    setAttachPreview(null);
  };

  // History helpers
  const saveToHistory = useCallback(async (userMsg, assistantMsg, sessionId, isFirst, firstQuestion) => {
    try {
      const msgs = [
        { role: userMsg.role, content: userMsg.content, model_used: null },
        { role: assistantMsg.role, content: assistantMsg.content, model_used: assistantMsg.modelUsed || null },
      ];
      if (isFirst) {
        const res = await createChatSession(firstQuestion.slice(0, 80) || 'New Conversation', msgs);
        setCurrentSessionId(res.session_id);
        await fetchSessions();
      } else if (sessionId) {
        await updateChatSession(sessionId, msgs);
        await fetchSessions();
      }
    } catch { /* silently fail — don't interrupt the chat */ }
  }, [fetchSessions]);

  const loadSession = useCallback(async (sessionId) => {
    try {
      const data = await getChatSession(sessionId);
      if (data.error) return;
      const restored = data.messages.map((m, i) => ({
        id: `h-${sessionId}-${i}`,
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources: [],
        modelUsed: m.model_used || null,
        ragContextFound: null,
      }));
      setMessages([WELCOME_MESSAGE, ...restored]);
      setCurrentSessionId(sessionId);
      setHistoryOpen(false);
    } catch { /* silently fail */ }
  }, []);

  const startNewChat = () => {
    setMessages([WELCOME_MESSAGE]);
    setVisibleSources({});
    setInput('');
    setCurrentSessionId(null);
    setHistoryOpen(false);
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      await deleteChatSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) startNewChat();
    } catch { /* silently fail */ }
  };

  const handleSend = async (questionText) => {
    const question = (questionText || input).trim();
    const hasFile = !!attachedFile;
    if ((!question && !hasFile) || isLoading) return;

    const displayText = hasFile
      ? `📎 ${attachPreview?.name}${question ? `\n${question}` : ''}`
      : question;

    setInput('');
    const fileToSend = attachedFile;
    const fileQuestion = question || 'Please analyse this file.';
    if (hasFile) clearAttachment();

    const userMsg = {
      id: `u-${++messageIdCounter}`,
      role: 'user',
      content: displayText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    const isFirstMessage = messages.filter(m => m.id !== 'welcome').length === 0;
    const sessionIdSnapshot = currentSessionId;

    try {
      const history = buildHistory([...messages, userMsg]);
      const startTime = Date.now();
      const data = hasFile
        ? await askWithFile(fileToSend, fileQuestion, history.slice(0, -1))
        : await askBankingFAQ(question, history.slice(0, -1));
      const responseTimeMs = Date.now() - startTime;

      const assistantMsg = {
        id: `a-${++messageIdCounter}`,
        role: 'assistant',
        content: data.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources: data.sources || [],
        modelUsed: data.model_used,
        ragContextFound: data.rag_context_found,
        detectedLanguage: data.detected_language || 'English',
        responseTimeMs,
      };
      setMessages(prev => [...prev, assistantMsg]);

      // Auto-save to history
      saveToHistory(userMsg, assistantMsg, sessionIdSnapshot, isFirstMessage, displayText);
    } catch {
      toast.error('Failed to reach the banking assistant. Please try again.', { duration: 4000 });
      setMessages(prev => [...prev, {
        id: `e-${++messageIdCounter}`,
        role: 'assistant',
        content: 'I apologize, I encountered an issue. Please try again or call 1800-XXX-XXXX.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources: [], modelUsed: 'error', ragContextFound: false,
      }]);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleClear = () => {
    setMessages([WELCOME_MESSAGE]);
    setVisibleSources({});
    setInput('');
    setCurrentSessionId(null);
  };

  const handleDownloadPdf = useCallback(async () => {
    if (messages.length <= 1) return; // nothing beyond welcome
    try {
      const userName = currentUser?.fullName || null;
      const blob = await pdf(
        <ChatPdfDocument messages={messages} userName={userName} />
      ).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const dateStr = new Date().toISOString().slice(0, 10);
      a.download = `chat-history-${dateStr}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Chat history downloaded as PDF!', { duration: 3000 });
    } catch (err) {
      console.error('PDF generation error:', err);
      toast.error('Failed to generate PDF. Please try again.', { duration: 4000 });
    }
  }, [messages, currentUser]);

  return (
    <div className="db-root">
      {/* ── Global Header ── */}
      <header className="db-topbar">
        <div className="db-topbar-left">
          <span className="db-topbar-icon">🏛️</span>
          <div>
            <h1 className="db-topbar-title">The World Bank</h1>
            <p className="db-topbar-sub">AI Banking Assistant · RAG + GenAI</p>
          </div>
        </div>

        {/* Mobile tab switcher */}
        <div className="db-tabs">
          <button
            className={`db-tab ${activeTab === 'dashboard' ? 'db-tab--active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            📊 Dashboard
          </button>
          <button
            className={`db-tab ${activeTab === 'chat' ? 'db-tab--active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            💬 Chatbot
          </button>
        </div>

        <div className="db-topbar-right">
          <span className="status-badge">
            <span className="status-badge__dot" />
            Online 24/7
          </span>
          {currentUser && <span className="user-greeting">👤 {currentUser.fullName}</span>}
          <button
            className="clear-btn"
            onClick={handleDownloadPdf}
            title="Download chat history as PDF"
            disabled={messages.length <= 1}
            style={{ opacity: messages.length <= 1 ? 0.4 : 1, cursor: messages.length <= 1 ? 'not-allowed' : 'pointer' }}
          >
            📄 PDF
          </button>
          <button className="clear-btn" onClick={handleClear} title="New chat">🗑️</button>
          <button className="clear-btn logout-btn" onClick={handleLogout} title="Sign out">↩ Sign Out</button>
        </div>
      </header>

      {/* ── Body: Left Tabbed Panel + Right Chat ── */}
      <div className="db-body">
        {/* Left: tabbed panel – Account Details | Chat History */}
        <div className={`db-left ${activeTab === 'dashboard' ? 'db-panel--active' : ''}`}>
          <div className="db-left__tabs">
            <button
              className={`db-left__tab ${!historyOpen ? 'db-left__tab--active' : ''}`}
              onClick={() => setHistoryOpen(false)}
            >🏦 Account</button>
            <button
              className={`db-left__tab ${historyOpen ? 'db-left__tab--active' : ''}`}
              onClick={() => { setHistoryOpen(true); fetchSessions(); }}
            >🕐 History</button>
          </div>

          {/* Account Details tab */}
          {!historyOpen && (
            <div className="db-left__content">
              <DashboardPanel
                dashboard={dashboard}
                loading={dashLoading}
                onRefresh={fetchDashboard}
              />
            </div>
          )}

          {/* Chat History tab */}
          {historyOpen && (
            <div className="db-left__content">
              <div className="history-panel history-panel--side">
                <div className="history-panel__header">
                  <span>💬 Chat History</span>
                  <button className="history-panel__new" onClick={startNewChat}>+ New Chat</button>
                </div>
                {sessions.length === 0 ? (
                  <p className="history-panel__empty">No saved conversations yet.<br /><small>Start chatting and sessions will appear here.</small></p>
                ) : (
                  <ul className="history-list">
                    {sessions.map(s => (
                      <li
                        key={s.id}
                        className={`history-item ${s.id === currentSessionId ? 'history-item--active' : ''}`}
                        onClick={() => loadSession(s.id)}
                      >
                        <div className="history-item__title">{s.title}</div>
                        <div className="history-item__meta">
                          {new Date(s.updated_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                        </div>
                        <button
                          className="history-item__delete"
                          onClick={(e) => handleDeleteSession(e, s.id)}
                          title="Delete"
                        >✕</button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right: chatbot */}
        <div className={`db-right ${activeTab === 'chat' ? 'db-panel--active' : ''}`}>
          <div className="chatbot-layout db-chat-inner">

            {/* Quick chips */}
            {messages.length === 1 && (
              <div className="quick-questions">
                <p className="quick-questions__label">Quick questions:</p>
                <div className="quick-questions__chips">
                  {QUICK_QUESTIONS.map((q, i) => (
                    <button key={i} className="quick-chip" onClick={() => handleSend(q)} disabled={isLoading}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Messages */}
            <div className="chat-messages">
              {messages.map((msg) => (
                <React.Fragment key={msg.id}>
                  <ChatMessage message={msg} onToggleSources={toggleSources} />
                  {msg.role === 'assistant' && msg.sources?.length > 0 && (
                    <SourceCitations sources={msg.sources} isVisible={!!visibleSources[msg.id]} />
                  )}
                </React.Fragment>
              ))}
              {isLoading && <ThinkingIndicator />}
              <div ref={chatEndRef} />
            </div>

            {/* Input bar */}
            <footer className="chatbot-footer">
              {/* Attachment preview chip */}
              {attachPreview && (
                <div className="attach-preview">
                  {attachPreview.isImage && attachPreview.objectUrl && (
                    <img src={attachPreview.objectUrl} alt="preview" className="attach-preview__thumb" />
                  )}
                  {!attachPreview.isImage && <span className="attach-preview__icon">📄</span>}
                  <span className="attach-preview__name">{attachPreview.name}</span>
                  <button className="attach-preview__remove" onClick={clearAttachment} aria-label="Remove attachment">✕</button>
                </div>
              )}

              <div className="chatbot-input-bar">
                {/* Hidden file input */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif,application/pdf"
                  style={{ display: 'none' }}
                  onChange={handleFileSelect}
                />

                {/* Paperclip attach button */}
                <button
                  className="attach-btn"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading}
                  title="Attach image or PDF"
                  aria-label="Attach file"
                >
                  📎
                </button>

                <textarea
                  ref={inputRef}
                  className="chatbot-input"
                  placeholder={attachedFile ? 'Ask a question about your file… (or send as-is)' : 'Ask about accounts, loans, cards, transfers…'}
                  value={input}
                  onChange={(e) => setInput(e.target.value.slice(0, 2000))}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                  rows={1}
                  maxLength={2000}
                  aria-label="Chat input"
                />
                <button
                  className="send-btn"
                  onClick={() => handleSend()}
                  disabled={isLoading || (!input.trim() && !attachedFile) || input.length > 2000}
                  aria-label="Send message"
                >
                  {isLoading ? <span className="send-btn__spinner" /> : <span>↑</span>}
                </button>
              </div>
              {input.length > 0 && (
                <div className={`char-counter ${input.length >= 1800 ? (input.length >= 2000 ? 'char-counter--error' : 'char-counter--warn') : ''}`}>
                  {input.length} / 2000
                </div>
              )}
              <p className="chatbot-footer__disclaimer">
                World Bank AI Assistant · RAG-grounded · All data is strictly access-controlled.
              </p>
            </footer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;

import axios from 'axios';
import { getToken } from './auth';

const API_BASE = 'http://localhost:8000';

const api = axios.create({ baseURL: API_BASE });

// Attach JWT to every request automatically
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Banking / Public Chat → both hit /process ─────────────────────────────────
// The `api` axios instance attaches the JWT automatically when the user is
// logged in. Guests have no token, so /process treats them as anonymous and
// returns RAG-grounded answers (personal queries are deflected to login).
export const askBankingFAQ = async (question, conversationHistory = []) => {
  const res = await api.post('/process', {
    question,
    conversation_history: conversationHistory,
  });
  return res.data;
};

export const askWithFile = async (file, question, conversationHistory = []) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('question', question || 'Please analyse this file.');
  formData.append('conversation_history', JSON.stringify(
    conversationHistory.map(t => ({ role: t.role, content: t.content }))
  ));
  const res = await api.post('/process/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

// ── Customer Dashboard ─────────────────────────────────────────────────────────
export const getCustomerDashboard = async () => {
  const res = await api.get('/customer/dashboard');
  return res.data;
};

// ── Manager ───────────────────────────────────────────────────────────────────
export const getAllCustomers = async () => {
  const res = await api.get('/manager/customers');
  return res.data;
};

export const createCustomer = async (data) => {
  const res = await api.post('/manager/customers', data);
  return res.data;
};

// ── Chat History ───────────────────────────────────────────────────────────────
export const createChatSession = async (title, messages = []) => {
  const res = await api.post('/history/sessions', { title, messages });
  return res.data; // { session_id }
};

export const updateChatSession = async (sessionId, messages, title = null) => {
  const body = { messages };
  if (title) body.title = title;
  const res = await api.put(`/history/sessions/${sessionId}`, body);
  return res.data;
};

export const listChatSessions = async () => {
  const res = await api.get('/history/sessions');
  return res.data; // { sessions: [...] }
};

export const getChatSession = async (sessionId) => {
  const res = await api.get(`/history/sessions/${sessionId}`);
  return res.data; // { session, messages }
};

export const deleteChatSession = async (sessionId) => {
  const res = await api.delete(`/history/sessions/${sessionId}`);
  return res.data;
};

// ── Translation ────────────────────────────────────────────────────────────────
export const translateMessage = async (text, targetLanguage) => {
  const res = await api.post('/chat/translate', { text, target_language: targetLanguage });
  return res.data; // { translated_text, target_language }
};

export default api;

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Home from './pages/Home';
import ManagerDashboard from './pages/ManagerDashboard';
import { isAuthenticated, isManager } from './services/auth';
import './App.css';

// Protected route – redirects to /login if not authenticated
const ProtectedRoute = ({ children, managerOnly = false }) => {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (managerOnly && !isManager()) return <Navigate to="/chat" replace />;
  return children;
};

// Public-only route (login) – redirect if already logged in
const PublicRoute = ({ children }) => {
  if (isAuthenticated()) {
    return <Navigate to={isManager() ? '/manager' : '/chat'} replace />;
  }
  return children;
};

const App = () => (
  <BrowserRouter>
    <Toaster position="top-right" />
    <Routes>
      {/* Landing page – always public */}
      <Route path="/" element={<Landing />} />

      {/* Login – redirect to chat if already logged in */}
      <Route path="/login" element={
        <PublicRoute><Login /></PublicRoute>
      } />

      {/* Authenticated customer dashboard + chat */}
      <Route path="/chat" element={
        <ProtectedRoute><Home /></ProtectedRoute>
      } />

      {/* Manager only */}
      <Route path="/manager" element={
        <ProtectedRoute managerOnly><ManagerDashboard /></ProtectedRoute>
      } />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </BrowserRouter>
);

export default App;

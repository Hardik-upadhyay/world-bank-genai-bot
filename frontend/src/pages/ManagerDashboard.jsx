import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { logout, getCurrentUser } from '../services/auth';
import { getAllCustomers, createCustomer } from '../services/api';

const ManagerDashboard = () => {
  const navigate = useNavigate();
  const user = getCurrentUser();

  const [customers, setCustomers]     = useState([]);
  const [loading, setLoading]         = useState(true);
  const [showForm, setShowForm]       = useState(false);
  const [formData, setFormData]       = useState({
    username: '', password: '', full_name: '', email: '',
    phone: '', address: '', account_type: 'Savings',
    initial_balance: 0, currency: 'USD', branch: 'World Bank HQ',
  });
  const [formError, setFormError]   = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [submitting, setSubmitting]   = useState(false);

  useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      const data = await getAllCustomers();
      setCustomers(data.customers || []);
    } catch {
      setCustomers([]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => { logout(); navigate('/'); };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleCreateCustomer = async (e) => {
    e.preventDefault();
    setFormError(''); setFormSuccess(''); setSubmitting(true);
    try {
      const result = await createCustomer({
        ...formData,
        initial_balance: parseFloat(formData.initial_balance) || 0,
      });
      setFormSuccess(`Customer created! Account: ${result.account_number} | ID: ${result.customer_id}`);
      setFormData({ username: '', password: '', full_name: '', email: '', phone: '', address: '',
                    account_type: 'Savings', initial_balance: 0, currency: 'USD', branch: 'World Bank HQ' });
      setShowForm(false);
      fetchCustomers();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Failed to create customer.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="manager-layout">
      {/* Header */}
      <header className="manager-header">
        <div className="manager-header__left">
          <span className="manager-logo-icon">🏛️</span>
          <div>
            <div className="manager-title">The World Bank</div>
            <div className="manager-subtitle">Manager Dashboard</div>
          </div>
        </div>
        <div className="manager-header__right">
          <span className="manager-user-badge">👤 {user?.fullName}</span>
          <button className="manager-logout-btn" onClick={handleLogout}>Sign Out</button>
        </div>
      </header>

      <div className="manager-content">
        {/* Stats Row */}
        <div className="manager-stats">
          <div className="stat-card">
            <div className="stat-card__value">{customers.length}</div>
            <div className="stat-card__label">Total Customers</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__value">
              ${customers.reduce((s, c) => s + (c.total_balance || 0), 0).toLocaleString(undefined, {maximumFractionDigits:0})}
            </div>
            <div className="stat-card__label">Total AUM (USD)</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__value">{customers.reduce((s, c) => s + (c.account_count || 0), 0)}</div>
            <div className="stat-card__label">Total Accounts</div>
          </div>
        </div>

        {/* Success Banner */}
        {formSuccess && (
          <div className="manager-alert manager-alert--success">✅ {formSuccess}</div>
        )}

        {/* Customer Table Section */}
        <div className="manager-section">
          <div className="manager-section__header">
            <h2 className="manager-section__title">Customer Portfolio</h2>
            <button className="manager-add-btn" onClick={() => { setShowForm(!showForm); setFormError(''); setFormSuccess(''); }}>
              {showForm ? '✕ Cancel' : '+ New Customer'}
            </button>
          </div>

          {/* Create Customer Form */}
          {showForm && (
            <form className="manager-form" onSubmit={handleCreateCustomer}>
              <h3 className="manager-form__title">Create New Customer</h3>
              <div className="manager-form__grid">
                {[
                  { name: 'full_name',  label: 'Full Name',    type: 'text',   placeholder: 'Jane Doe',       required: true },
                  { name: 'username',   label: 'Username',     type: 'text',   placeholder: 'jane.doe',       required: true },
                  { name: 'password',   label: 'Password',     type: 'password', placeholder: 'Min 6 chars',  required: true },
                  { name: 'email',      label: 'Email',        type: 'email',  placeholder: 'jane@email.com', required: true },
                  { name: 'phone',      label: 'Phone',        type: 'text',   placeholder: '+1-555-0000',    required: false },
                  { name: 'address',    label: 'Address',      type: 'text',   placeholder: 'City, Country',  required: false },
                  { name: 'branch',     label: 'Branch',       type: 'text',   placeholder: 'World Bank HQ',  required: false },
                  { name: 'initial_balance', label: 'Initial Balance (USD)', type: 'number', placeholder: '0', required: false },
                ].map(f => (
                  <div className="manager-field" key={f.name}>
                    <label className="manager-label">{f.label}</label>
                    <input
                      className="manager-input"
                      name={f.name} type={f.type} placeholder={f.placeholder}
                      value={formData[f.name]} onChange={handleInputChange}
                      required={f.required}
                    />
                  </div>
                ))}
                <div className="manager-field">
                  <label className="manager-label">Account Type</label>
                  <select name="account_type" className="manager-input" value={formData.account_type} onChange={handleInputChange}>
                    <option>Savings</option><option>Current</option>
                    <option>Fixed Deposit</option><option>Checking</option>
                  </select>
                </div>
                <div className="manager-field">
                  <label className="manager-label">Currency</label>
                  <select name="currency" className="manager-input" value={formData.currency} onChange={handleInputChange}>
                    <option>USD</option><option>EUR</option><option>GBP</option><option>INR</option>
                  </select>
                </div>
              </div>
              {formError && <div className="manager-alert manager-alert--error">⚠️ {formError}</div>}
              <button type="submit" className="manager-submit-btn" disabled={submitting}>
                {submitting ? 'Creating…' : 'Create Customer'}
              </button>
            </form>
          )}

          {/* Customers Table */}
          {loading ? (
            <div className="manager-loading">Loading customers…</div>
          ) : customers.length === 0 ? (
            <div className="manager-empty">No customers yet. Create the first one above.</div>
          ) : (
            <div className="manager-table-wrap">
              <table className="manager-table">
                <thead>
                  <tr>
                    <th>Customer ID</th><th>Name</th><th>Email</th>
                    <th>Accounts</th><th>Total Balance</th><th>KYC</th><th>Since</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map(c => (
                    <tr key={c.id}>
                      <td><code>{c.customer_id}</code></td>
                      <td><strong>{c.full_name}</strong></td>
                      <td>{c.email}</td>
                      <td style={{textAlign:'center'}}>{c.account_count}</td>
                      <td><strong>${(c.total_balance || 0).toLocaleString(undefined,{minimumFractionDigits:2})}</strong></td>
                      <td><span className={`kyc-badge kyc-badge--${c.kyc_status?.toLowerCase()}`}>{c.kyc_status}</span></td>
                      <td>{c.created_at?.slice(0,10)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ManagerDashboard;

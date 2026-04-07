import React, { useState } from 'react';

const MAX_CHARS = 2000;

const InputBox = ({ onSubmit, isLoading }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && input.length <= MAX_CHARS) {
      onSubmit(input);
    }
  };

  const handleChange = (e) => {
    setInput(e.target.value.slice(0, MAX_CHARS));
  };

  const atLimit = input.length >= MAX_CHARS;
  const nearLimit = input.length >= MAX_CHARS * 0.9;

  return (
    <div className="w-full max-w-2xl mx-auto mt-8">
      <form onSubmit={handleSubmit} className="relative shadow-lg rounded-2xl overflow-hidden bg-white border border-slate-200">
        <textarea
          className="w-full text-slate-800 p-4 pb-12 rounded-2xl border-none focus:ring-0 resize-none outline-none min-h-[120px]"
          placeholder="Ask an AI question or enter problem..."
          value={input}
          onChange={handleChange}
          disabled={isLoading}
          maxLength={MAX_CHARS}
        />
        {/* Character counter */}
        {input.length > 0 && (
          <div
            style={{
              position: 'absolute',
              bottom: '3.2rem',
              right: '1rem',
              fontSize: '11px',
              fontWeight: 600,
              color: atLimit ? '#ef4444' : nearLimit ? '#f59e0b' : '#94a3b8',
              userSelect: 'none',
            }}
          >
            {input.length} / {MAX_CHARS}
          </div>
        )}
        <div className="absolute bottom-3 right-3">
          <button
            type="submit"
            disabled={isLoading || !input.trim() || atLimit}
            className="flex items-center justify-center bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-medium py-2 px-5 rounded-xl transition-colors duration-200 shadow-sm"
          >
            {isLoading ? 'Sending...' : 'Generate 🚀'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default InputBox;

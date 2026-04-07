import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ResultCard from '../components/ResultCard';

const Results = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { input, result, explanation } = location.state || {};

  if (!input) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <p className="text-slate-600 mb-4">No results found.</p>
          <button 
            onClick={() => navigate('/')} 
            className="text-indigo-600 hover:text-indigo-800 font-medium font-semibold"
          >
            Go back Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="max-w-4xl mx-auto mb-8 flex justify-between items-center">
        <h2 className="text-3xl font-bold text-slate-800">Results 🎯</h2>
        <button 
          onClick={() => navigate('/')}
          className="bg-white text-slate-700 hover:bg-slate-100 border border-slate-200 py-2 px-4 rounded-lg shadow-sm transition-colors font-medium cursor-pointer"
        >
          ← New Generation
        </button>
      </div>

      <div className="mb-8">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2 ml-1">Original Prompt</h3>
        <div className="bg-indigo-50 text-indigo-900 p-4 rounded-xl border border-indigo-100 italic">
          "{input}"
        </div>
      </div>

      <ResultCard 
        title="Final Answer / Output" 
        content={result} 
        type="primary" 
      />

      <ResultCard 
        title="DeepSeek R1 Reasoning Explanation 🧠" 
        content={explanation} 
        type="secondary" 
      />
    </div>
  );
};

export default Results;

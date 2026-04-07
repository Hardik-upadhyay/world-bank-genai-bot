import React from 'react';

const ResultCard = ({ title, content, type = "primary" }) => {
  // Determine gradient/colors based on type
  const isExplanation = type === "secondary";
  const bgClass = isExplanation ? "bg-slate-50 border-slate-200" : "bg-white border-indigo-100";
  const titleColor = isExplanation ? "text-slate-600" : "text-indigo-700";
  const borderTop = isExplanation ? "border-t-4 border-slate-400" : "border-t-4 border-indigo-500";

  return (
    <div className={`w-full max-w-4xl mx-auto rounded-xl shadow-md p-6 mb-6 border ${bgClass} ${borderTop}`}>
      <h3 className={`text-lg font-semibold mb-3 ${titleColor}`}>{title}</h3>
      <div className="text-slate-700 whitespace-pre-wrap leading-relaxed">
        {content}
      </div>
    </div>
  );
};

export default ResultCard;

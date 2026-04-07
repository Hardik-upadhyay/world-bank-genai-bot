import React from 'react';

const Loader = () => {
  return (
    <div className="flex flex-col items-center justify-center space-y-3">
      <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      <p className="text-sm text-indigo-500 font-medium">Processing request...</p>
    </div>
  );
};

export default Loader;

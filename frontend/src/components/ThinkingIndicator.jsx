import React from 'react';

const ThinkingIndicator = () => (
  <div className="chat-message chat-message--assistant">
    <div className="chat-avatar">
      <span className="chat-avatar__icon">🏦</span>
    </div>
    <div className="chat-bubble chat-bubble--assistant chat-bubble--thinking">
      <div className="thinking-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span className="thinking-label">Searching knowledge base...</span>
    </div>
  </div>
);

export default ThinkingIndicator;

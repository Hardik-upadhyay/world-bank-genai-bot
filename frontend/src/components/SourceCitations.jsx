import React, { useState } from 'react';

const SourceCitations = ({ sources, isVisible }) => {
  const [expanded, setExpanded] = useState(null);

  if (!isVisible || !sources || sources.length === 0) return null;

  return (
    <div className="citations-panel">
      <div className="citations-panel__header">
        <span className="citations-panel__title">📚 Knowledge Base Sources</span>
        <span className="citations-panel__count">{sources.length} retrieved</span>
      </div>
      <div className="citations-panel__list">
        {sources.map((src, idx) => (
          <div key={idx} className="citation-card">
            <div
              className="citation-card__header"
              onClick={() => setExpanded(expanded === idx ? null : idx)}
              role="button"
              tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && setExpanded(expanded === idx ? null : idx)}
            >
              <div className="citation-card__left">
                <span className="citation-topic-badge">{src.topic}</span>
                <span className="citation-source">{src.source}</span>
              </div>
              <div className="citation-card__right">
                <span className="citation-relevance">
                  {Math.round(src.relevance_score * 100)}% match
                </span>
                <span className="citation-chevron">{expanded === idx ? '▲' : '▼'}</span>
              </div>
            </div>
            {expanded === idx && (
              <div className="citation-card__body">
                <p className="citation-excerpt">{src.excerpt}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default SourceCitations;

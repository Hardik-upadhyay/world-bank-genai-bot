import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { pdf, Document, Page, Text, View, StyleSheet } from '@react-pdf/renderer';
import { translateMessage } from '../services/api';

// ── Supported Languages ───────────────────────────────────────────────────────

const LANGUAGES = [
  { code: 'hi', label: '🇮🇳 Hindi' },
  { code: 'es', label: '🇪🇸 Spanish' },
  { code: 'fr', label: '🇫🇷 French' },
  { code: 'de', label: '🇩🇪 German' },
  { code: 'zh', label: '🇨🇳 Chinese' },
  { code: 'ar', label: '🇸🇦 Arabic' },
  { code: 'pt', label: '🇧🇷 Portuguese' },
  { code: 'ja', label: '🇯🇵 Japanese' },
  { code: 'ko', label: '🇰🇷 Korean' },
  { code: 'ru', label: '🇷🇺 Russian' },
  { code: 'it', label: '🇮🇹 Italian' },
  { code: 'ta', label: '🇮🇳 Tamil' },
  { code: 'en', label: '🇬🇧 English' },
];

// ── Table detection & parsing ─────────────────────────────────────────────────

function hasMarkdownTable(content) {
  if (!content) return false;
  const lines = content.split('\n');
  const hasPipes = lines.some(l => l.includes('|') && l.trim().startsWith('|'));
  const hasSep   = lines.some(l => /^\|[\s\-|:]+\|/.test(l.trim()));
  return hasPipes && hasSep;
}

function parseMarkdownTable(content) {
  const lines = content.split('\n').filter(l => l.includes('|') && l.trim().startsWith('|'));
  const dataLines = lines.filter(l => !/^\|[\s\-|:]+\|/.test(l.trim()));
  const parseCells = (line) =>
    line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
  if (dataLines.length === 0) return { headers: [], rows: [] };
  const [headerLine, ...rowLines] = dataLines;
  return { headers: parseCells(headerLine), rows: rowLines.map(parseCells) };
}

// ── CSV export ────────────────────────────────────────────────────────────────

function downloadCSV(content, filename = 'data.csv') {
  const { headers, rows } = parseMarkdownTable(content);
  if (headers.length === 0) return;
  const escape = (v) => `"${String(v).replace(/"/g, '""')}"`;
  const csvLines = [
    headers.map(escape).join(','),
    ...rows.map(r => r.map(escape).join(',')),
  ];
  const blob = new Blob([csvLines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

// ── PDF export ────────────────────────────────────────────────────────────────

const pdfStyles = StyleSheet.create({
  page:        { padding: 36, fontFamily: 'Helvetica', fontSize: 9, backgroundColor: '#ffffff' },
  title:       { fontSize: 15, fontWeight: 'bold', marginBottom: 4, color: '#1e3a8a' },
  subtitle:    { fontSize: 8, color: '#6b7280', marginBottom: 14 },
  table:       { width: '100%' },
  rowHead:     { flexDirection: 'row', backgroundColor: '#1e3a8a', borderRadius: 2 },
  rowEven:     { flexDirection: 'row', backgroundColor: '#f9fafb', borderBottomWidth: 1, borderBottomColor: '#e5e7eb' },
  rowOdd:      { flexDirection: 'row', backgroundColor: '#ffffff', borderBottomWidth: 1, borderBottomColor: '#e5e7eb' },
  cellHead:    { padding: '5 6', color: '#ffffff', fontWeight: 'bold', fontSize: 8, flexWrap: 'wrap', overflow: 'hidden' },
  cell:        { padding: '4 6', color: '#111827', fontSize: 8, flexWrap: 'wrap', overflow: 'hidden' },
  footer:      { marginTop: 16, fontSize: 7, color: '#9ca3af', textAlign: 'center' },
  headerBorder:{ borderWidth: 1, borderColor: '#1e3a8a', borderRadius: 2, marginBottom: 0 },
});

function TablePDFDoc({ headers, rows, title }) {
  const colPct = headers.length > 0 ? `${(100 / headers.length).toFixed(2)}%` : '100%';
  return (
    <Document>
      <Page size="A4" orientation={headers.length > 5 ? 'landscape' : 'portrait'} style={pdfStyles.page} wrap>
        <Text style={pdfStyles.title}>{title}</Text>
        <Text style={pdfStyles.subtitle}>
          Generated {new Date().toLocaleString()} · {rows.length} record{rows.length !== 1 ? 's' : ''}
        </Text>
        <View style={pdfStyles.table}>
          <View style={[pdfStyles.rowHead, pdfStyles.headerBorder]} fixed>
            {headers.map((h, i) => (
              <Text key={i} style={[pdfStyles.cellHead, { width: colPct }]}>{h}</Text>
            ))}
          </View>
          {rows.map((row, ri) => (
            <View key={ri} style={ri % 2 === 0 ? pdfStyles.rowEven : pdfStyles.rowOdd} wrap={false}>
              {headers.map((_, ci) => (
                <Text key={ci} style={[pdfStyles.cell, { width: colPct }]}>{row[ci] ?? ''}</Text>
              ))}
            </View>
          ))}
        </View>
        <Text style={pdfStyles.footer} fixed>The World Bank · AI Banking Assistant · Confidential</Text>
      </Page>
    </Document>
  );
}

async function downloadPDF(content, title = 'Report') {
  const { headers, rows } = parseMarkdownTable(content);
  if (headers.length === 0) return;
  const blob = await pdf(<TablePDFDoc headers={headers} rows={rows} title={title} />).toBlob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = `${title.replace(/\s+/g, '_')}.pdf`; a.click();
  URL.revokeObjectURL(url);
}

// ── Response time formatter ───────────────────────────────────────────────────

function fmtTime(ms) {
  if (!ms && ms !== 0) return null;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

// ── Translate dropdown component ──────────────────────────────────────────────

const TranslateButton = ({ originalContent }) => {
  const [open, setOpen]             = useState(false);
  const [isLoading, setIsLoading]   = useState(false);
  const [translated, setTranslated] = useState(null); // { lang, text }
  const [showOriginal, setShowOriginal] = useState(false);
  const ref = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSelect = async (lang) => {
    setOpen(false);
    if (translated?.lang === lang.label) { setShowOriginal(false); return; }
    setIsLoading(true);
    try {
      const res = await translateMessage(originalContent, lang.label.replace(/^.+?\s/, '')); // strip flag emoji
      setTranslated({ lang: lang.label, text: res.translated_text });
      setShowOriginal(false);
    } catch {
      /* silently fall back */
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <span className="translate-wrapper" ref={ref}>
      {/* Main translate button */}
      <button
        className={`translate-btn${isLoading ? ' translate-btn--loading' : ''}`}
        onClick={() => !isLoading && setOpen(o => !o)}
        title="Translate this message"
        disabled={isLoading}
      >
        {isLoading ? '⟳' : '🌐'} {isLoading ? 'Translating…' : 'Translate'}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="translate-dropdown">
          {LANGUAGES.map(lang => (
            <button
              key={lang.code}
              className="translate-option"
              onClick={() => handleSelect(lang)}
            >
              {lang.label}
            </button>
          ))}
        </div>
      )}

      {/* Show translated / show original toggle */}
      {translated && !isLoading && (
        <button
          className="translate-toggle"
          onClick={() => setShowOriginal(o => !o)}
        >
          {showOriginal ? `Show ${translated.lang}` : 'Show original'}
        </button>
      )}

      {/* Translated content overlay (returned as a data attr for parent to use) */}
      {translated && !isLoading && (
        <span
          className="translate-result-data"
          data-translated={!showOriginal ? translated.text : ''}
        />
      )}
    </span>
  );
};

// ── Main ChatMessage component ────────────────────────────────────────────────

const ChatMessage = ({ message, onToggleSources }) => {
  const isUser   = message.role === 'user';
  const hasTable = !isUser && hasMarkdownTable(message.content);
  const timeFmt  = !isUser ? fmtTime(message.responseTimeMs) : null;

  // Translate state lifted up so content area can use it
  const [translatedText, setTranslatedText] = useState(null);
  const [isTranslating, setIsTranslating]   = useState(false);
  const [translateOpen, setTranslateOpen]   = useState(false);
  const [translatedLang, setTranslatedLang] = useState(null);
  const [showOriginal, setShowOriginal]     = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setTranslateOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleTranslate = async (lang) => {
    setTranslateOpen(false);
    if (translatedLang === lang.label) { setShowOriginal(false); return; }
    setIsTranslating(true);
    try {
      const langName = lang.label.replace(/^\S+\s/, ''); // strip flag
      const res = await translateMessage(message.content, langName);
      setTranslatedText(res.translated_text);
      setTranslatedLang(lang.label);
      setShowOriginal(false);
    } catch { /* silently fail */ }
    finally { setIsTranslating(false); }
  };

  const displayContent = (!showOriginal && translatedText) ? translatedText : message.content;

  const handleCSV = () => downloadCSV(displayContent, 'world_bank_data.csv');
  const handlePDF = () => downloadPDF(displayContent, 'World Bank Report');

  return (
    <div className={`chat-message ${isUser ? 'chat-message--user' : 'chat-message--assistant'}`}>
      {!isUser && (
        <div className="chat-avatar">
          <span className="chat-avatar__icon">🏦</span>
        </div>
      )}

      <div className={`chat-bubble ${isUser ? 'chat-bubble--user' : 'chat-bubble--assistant'}`}>
        {/* Message text */}
        <div className="chat-bubble__text">
          {isUser ? (
            message.content
          ) : (
            <div className="markdown-body">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
                  code: ({ node, inline, className, children, ...props }) =>
                    inline ? (
                      <code className="md-code-inline" {...props}>{children}</code>
                    ) : (
                      <pre className="md-code-block"><code {...props}>{children}</code></pre>
                    ),
                }}
              >
                {displayContent}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Translation indicator */}
        {!isUser && translatedText && !showOriginal && (
          <div className="translate-indicator">
            Translated to {translatedLang}
            <button className="translate-revert" onClick={() => setShowOriginal(true)}>
              Show original
            </button>
          </div>
        )}
        {!isUser && showOriginal && translatedText && (
          <div className="translate-indicator translate-indicator--original">
            Showing original
            <button className="translate-revert" onClick={() => setShowOriginal(false)}>
              Show {translatedLang}
            </button>
          </div>
        )}

        {/* Assistant meta bar */}
        {!isUser && (
          <div className="chat-bubble__meta">
            {/* Response time badge */}
            {timeFmt && (
              <span className="response-time-badge" title="Response time">
                ⚡ {timeFmt}
              </span>
            )}

            {message.modelUsed && (
              <span className="model-badge">
                <span className="model-badge__dot"></span>
                {message.modelUsed}
              </span>
            )}
            {message.detectedLanguage && message.detectedLanguage.toLowerCase() !== 'english' && (
              <span className="lang-badge">🌐 {message.detectedLanguage}</span>
            )}
            {message.sources && message.sources.length > 0 && (
              <button className="sources-toggle" onClick={() => onToggleSources(message.id)} aria-label="Toggle source citations">
                📚 {message.sources.length} source{message.sources.length > 1 ? 's' : ''}
              </button>
            )}
            {message.ragContextFound === false && (
              <span className="no-rag-badge">⚠️ No KB context</span>
            )}

            {/* Download buttons */}
            {hasTable && (
              <span className="download-actions">
                <button className="download-btn download-btn--csv" onClick={handleCSV} title="Download as CSV">⬇ CSV</button>
                <button className="download-btn download-btn--pdf" onClick={handlePDF} title="Download as PDF">⬇ PDF</button>
              </span>
            )}

            {/* Translate button + dropdown */}
            {message.content && message.id !== 'welcome' && (
              <span className="translate-wrapper" ref={dropdownRef}>
                <button
                  className={`translate-btn${isTranslating ? ' translate-btn--loading' : ''}`}
                  onClick={() => !isTranslating && setTranslateOpen(o => !o)}
                  disabled={isTranslating}
                  title="Translate this response"
                >
                  {isTranslating ? '⟳ Translating…' : '🌐 Translate'}
                </button>
                {translateOpen && (
                  <div className="translate-dropdown">
                    {LANGUAGES.map(lang => (
                      <button
                        key={lang.code}
                        className={`translate-option${translatedLang === lang.label ? ' translate-option--active' : ''}`}
                        onClick={() => handleTranslate(lang)}
                      >
                        {lang.label}
                      </button>
                    ))}
                  </div>
                )}
              </span>
            )}
          </div>
        )}

        {/* Timestamp */}
        <div className={`chat-bubble__time ${isUser ? 'chat-bubble__time--user' : ''}`}>
          {message.timestamp || ''}
        </div>
      </div>

      {isUser && (
        <div className="chat-avatar chat-avatar--user">
          <span className="chat-avatar__icon">👤</span>
        </div>
      )}
    </div>
  );
};

export default ChatMessage;

import React from 'react';
import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
  Font,
} from '@react-pdf/renderer';

// ── Colour Palette ─────────────────────────────────────────────────────────────
const BRAND_BLUE   = '#1a3c6e';  // World Bank navy
const ACCENT       = '#2563eb';  // blue-600
const USER_BG      = '#eff6ff';  // blue-50
const USER_BORDER  = '#93c5fd';  // blue-300
const ASST_BG      = '#f8fafc';  // slate-50
const ASST_BORDER  = '#cbd5e1';  // slate-300
const TEXT_DARK    = '#1e293b';
const TEXT_MID     = '#64748b';
const TEXT_LIGHT   = '#94a3b8';
const ERROR_COL    = '#ef4444';

// ── Styles ─────────────────────────────────────────────────────────────────────
const S = StyleSheet.create({
  page: {
    backgroundColor: '#ffffff',
    paddingTop: 36,
    paddingBottom: 48,
    paddingHorizontal: 40,
    fontFamily: 'Helvetica',
    fontSize: 10,
    color: TEXT_DARK,
  },

  /* Header */
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 2,
    borderBottomColor: BRAND_BLUE,
    paddingBottom: 10,
    marginBottom: 18,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  headerIcon: { fontSize: 22 },
  headerTitle: { fontSize: 15, fontFamily: 'Helvetica-Bold', color: BRAND_BLUE },
  headerSub:   { fontSize: 8,  color: TEXT_MID, marginTop: 1 },
  headerRight: { alignItems: 'flex-end' },
  headerDate:  { fontSize: 8, color: TEXT_MID },
  headerLabel: { fontSize: 7, color: TEXT_LIGHT, marginTop: 1 },

  /* Section title */
  sectionTitle: {
    fontSize: 9,
    fontFamily: 'Helvetica-Bold',
    color: TEXT_MID,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 10,
  },

  /* Message bubble */
  bubble: {
    borderRadius: 6,
    marginBottom: 10,
    padding: 10,
    borderLeftWidth: 3,
  },
  bubbleUser: {
    backgroundColor: USER_BG,
    borderLeftColor: ACCENT,
  },
  bubbleAssistant: {
    backgroundColor: ASST_BG,
    borderLeftColor: ASST_BORDER,
  },
  bubbleError: {
    backgroundColor: '#fff5f5',
    borderLeftColor: ERROR_COL,
  },

  /* Bubble meta row */
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 5,
  },
  roleLabel: {
    fontSize: 8,
    fontFamily: 'Helvetica-Bold',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  roleLabelUser:      { color: ACCENT },
  roleLabelAssistant: { color: BRAND_BLUE },
  roleLabelError:     { color: ERROR_COL },
  timestamp: { fontSize: 7, color: TEXT_LIGHT },

  /* Badges */
  badgeRow: { flexDirection: 'row', gap: 4, marginBottom: 5 },
  badge: {
    fontSize: 6.5,
    borderRadius: 3,
    paddingVertical: 1,
    paddingHorizontal: 4,
    fontFamily: 'Helvetica-Bold',
  },
  modelBadge: { backgroundColor: '#f1f5f9', color: TEXT_MID },
  ragBadge:   { backgroundColor: '#dcfce7', color: '#166534' },
  ragBadgeNo: { backgroundColor: '#fef9c3', color: '#854d0e' },

  /* Message content */
  content: { fontSize: 9.5, lineHeight: 1.55, color: TEXT_DARK },

  /* Sources */
  sourceItem: { fontSize: 8, color: TEXT_MID, marginTop: 4 },
  sourceDot:  { color: ACCENT },

  /* Divider */
  divider: { borderBottomWidth: 0.5, borderBottomColor: '#e2e8f0', marginVertical: 6 },

  /* Footer */
  footer: {
    position: 'absolute',
    bottom: 20,
    left: 40,
    right: 40,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 0.5,
    borderTopColor: '#e2e8f0',
    paddingTop: 6,
  },
  footerText: { fontSize: 7, color: TEXT_LIGHT },
  pageNum:    { fontSize: 7, color: TEXT_LIGHT },
});

// ── Helper: strip markdown-ish syntax for plain PDF text ──────────────────────
const cleanContent = (text = '') =>
  text
    .replace(/\*\*(.*?)\*\*/g, '$1')   // bold
    .replace(/\*(.*?)\*/g,   '$1')   // italic
    .replace(/`([^`]+)`/g,   '$1')   // inline code
    .replace(/#{1,6}\s/g,    '')     // headings
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links
    .trim();

// ── Sub-component: single message bubble ──────────────────────────────────────
const MessageBubble = ({ msg, index }) => {
  const isUser      = msg.role === 'user';
  const isError     = msg.modelUsed === 'error';
  const isWelcome   = msg.id === 'welcome';

  const bubbleStyle = [
    S.bubble,
    isUser    ? S.bubbleUser :
    isError   ? S.bubbleError :
                S.bubbleAssistant,
  ];

  const labelStyle = [
    S.roleLabel,
    isUser    ? S.roleLabelUser :
    isError   ? S.roleLabelError :
                S.roleLabelAssistant,
  ];

  const roleText = isWelcome ? 'AI Assistant (Welcome)' :
                  isUser     ? 'YOU' :
                  isError    ? '[!] AI ASSISTANT' :
                               'AI ASSISTANT';

  return (
    <View style={bubbleStyle} wrap={false}>
      {/* Meta row */}
      <View style={S.metaRow}>
        <Text style={labelStyle}>{roleText}</Text>
        {msg.timestamp && <Text style={S.timestamp}>{msg.timestamp}</Text>}
      </View>

      {/* Model / RAG badges for assistant messages */}
      {!isUser && !isWelcome && (msg.modelUsed || msg.ragContextFound != null) && (
        <View style={S.badgeRow}>
          {msg.modelUsed && msg.modelUsed !== 'error' && (
            <Text style={[S.badge, S.modelBadge]}>{msg.modelUsed}</Text>
          )}
          {msg.ragContextFound != null && (
            <Text style={[S.badge, msg.ragContextFound ? S.ragBadge : S.ragBadgeNo]}>
              {msg.ragContextFound ? 'RAG: OK' : 'RAG: None'}
            </Text>
          )}
        </View>
      )}

      {/* Content */}
      <Text style={S.content}>{cleanContent(msg.content)}</Text>

      {/* Sources */}
      {Array.isArray(msg.sources) && msg.sources.length > 0 && (
        <>
          <View style={S.divider} />
          {msg.sources.slice(0, 5).map((src, i) => (
            <Text key={i} style={S.sourceItem}>
              {'> '}{src.title || src.source || `Source ${i + 1}`}
            </Text>
          ))}
        </>
      )}
    </View>
  );
};

// ── Main Document ──────────────────────────────────────────────────────────────
const ChatPdfDocument = ({ messages = [], userName = null, sessionDate = null }) => {
  const exportedAt = new Date().toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });

  const messageCount = messages.filter(m => m.id !== 'welcome').length;

  return (
    <Document
      title="World Bank AI Chat History"
      author="World Bank AI Assistant"
      creator="AI Banking Assistant"
      subject="Chat History Export"
    >
      <Page size="A4" style={S.page}>
        {/* Header */}
        <View style={S.header} fixed>
          <View style={S.headerLeft}>
            <View>
              <Text style={S.headerTitle}>THE WORLD BANK</Text>
              <Text style={S.headerSub}>AI Banking Assistant - Chat History Export</Text>
            </View>
          </View>
          <View style={S.headerRight}>
            <Text style={S.headerDate}>Exported: {exportedAt}</Text>
            {userName && <Text style={S.headerLabel}>User: {userName}</Text>}
            <Text style={S.headerLabel}>{messageCount} message{messageCount !== 1 ? 's' : ''}</Text>
          </View>
        </View>

        {/* Section title */}
        <Text style={S.sectionTitle}>Conversation Transcript</Text>

        {/* Messages */}
        {messages.map((msg, i) => (
          <MessageBubble key={msg.id || i} msg={msg} index={i} />
        ))}

        {/* Footer */}
        <View style={S.footer} fixed>
          <Text style={S.footerText}>
            World Bank AI Assistant · RAG-grounded · Confidential
          </Text>
          <Text
            style={S.pageNum}
            render={({ pageNumber, totalPages }) =>
              `Page ${pageNumber} of ${totalPages}`
            }
          />
        </View>
      </Page>
    </Document>
  );
};

export default ChatPdfDocument;

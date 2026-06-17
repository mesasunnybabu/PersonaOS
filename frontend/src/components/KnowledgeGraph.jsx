// frontend/src/components/KnowledgeGraph.jsx
//
// Enhanced knowledge graph — replaces KnowledgeMap.jsx for Phase 6.
// Shows topic bubbles, learning path connections, and detail panel.

import React, { useState, useEffect } from 'react';

// ── Learning Path Definition ──────────────────────────────────────────────────
// Defines which topics connect to which in the learning path

const LEARNING_PATH = {
  'variables':       'loops',
  'loops':           'functions',
  'functions':       'recursion',
  'recursion':       'data-structures',
  'data-structures': 'algorithms',
  'algorithms':      'oop',
  'oop':             'modules',
  'modules':         'error-handling',
  'error-handling':  'apis',
  'apis':            'databases',
  'databases':       'testing',
  'testing':         'async',
  'decorators':      'async',
  'debugging':       'error-handling',
  'file-handling':   'databases',
};

// ── Color helpers ─────────────────────────────────────────────────────────────

function getConfidenceColor(score) {
  if (score >= 0.8) return { bg: '#22c55e', text: '#fff',    border: '#16a34a', label: 'Strong' };
  if (score >= 0.5) return { bg: '#3b82f6', text: '#fff',    border: '#2563eb', label: 'Growing' };
  if (score >= 0.2) return { bg: '#eab308', text: '#713f12', border: '#ca8a04', label: 'Learning' };
  return                   { bg: '#e5e7eb', text: '#374151', border: '#d1d5db', label: 'New' };
}

function getBubbleSize(count) {
  if (count >= 10) return 80;
  if (count >= 5)  return 64;
  if (count >= 2)  return 52;
  return 44;
}

// ── Topic Bubble ──────────────────────────────────────────────────────────────

function TopicBubble({ topic, isSelected, onClick }) {
  const colors = getConfidenceColor(topic.confidence_score);
  const size   = getBubbleSize(topic.encounter_count);

  return (
    <button
      onClick={() => onClick(topic)}
      style={{
        width:           size,
        height:          size,
        backgroundColor: colors.bg,
        borderColor:     colors.border,
        color:           colors.text,
        outline:         isSelected ? `3px solid #6366f1` : 'none',
        outlineOffset:   '3px',
      }}
      className="rounded-full border-2 flex flex-col items-center justify-center
                 transition-all duration-200 hover:scale-110 shadow-sm hover:shadow-md
                 flex-shrink-0 cursor-pointer"
      title={`${topic.topic} — ${topic.encounter_count} sessions`}
    >
      <span className="font-bold text-center leading-tight px-1"
            style={{ fontSize: size > 60 ? 11 : 9 }}>
        {topic.topic}
      </span>
      <span style={{ fontSize: 9, opacity: 0.8 }}>{topic.encounter_count}×</span>
    </button>
  );
}

// ── Learning Path Connections ─────────────────────────────────────────────────
// Shows which topics connect to which with labeled arrows

function PathConnection({ from, to, known }) {
  return (
    <div className="flex items-center gap-1 text-xs">
      <span className={`font-medium ${known ? 'text-indigo-600' : 'text-gray-400'}`}>
        {from}
      </span>
      <span className="text-gray-300">→</span>
      <span className={`font-medium ${known ? 'text-indigo-400' : 'text-gray-300'}`}>
        {to}
      </span>
    </div>
  );
}

// ── Topic Detail Panel ────────────────────────────────────────────────────────

function TopicDetailPanel({ topic, userId, onClose }) {
  const [detail, setDetail] = useState(null);
  const colors = getConfidenceColor(topic.confidence_score);

  useEffect(() => {
    fetch(`http://localhost:8000/api/knowledge/${userId}/topic/${topic.topic}`)
      .then(r => r.json())
      .then(setDetail)
      .catch(() => setDetail(null));
  }, [topic.topic, userId]);

  const nextTopic = LEARNING_PATH[topic.topic];
  const pct       = Math.round(topic.confidence_score * 100);

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 mt-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className="px-3 py-1 rounded-full text-xs font-bold"
            style={{ backgroundColor: colors.bg, color: colors.text }}
          >
            {topic.topic}
          </div>
          <span className="text-xs text-gray-400">{colors.label}</span>
        </div>
        <button
          onClick={onClose}
          className="text-gray-300 hover:text-gray-500 text-xl leading-none"
        >×</button>
      </div>

      {/* Confidence Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-gray-500 mb-1.5">
          <span>Confidence</span>
          <span>{pct}% ({topic.encounter_count} sessions)</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${pct}%`, backgroundColor: colors.bg }}
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">
          {Math.max(0, 10 - topic.encounter_count)} more sessions to master this topic
        </p>
      </div>

      {/* Next in Learning Path */}
      {nextTopic && (
        <div className="bg-indigo-50 rounded-lg px-3 py-2 mb-3">
          <p className="text-xs font-semibold text-indigo-600 mb-0.5">📍 Next on your path</p>
          <p className="text-xs text-indigo-700">
            After mastering <strong>{topic.topic}</strong>, explore <strong>{nextTopic}</strong>
          </p>
        </div>
      )}

      {/* Recent Questions */}
      {detail?.recent_questions?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 mb-2">Recent questions:</p>
          <ul className="space-y-1">
            {detail.recent_questions.map((q, i) => (
              <li key={i} className="text-xs text-gray-600 bg-gray-50 rounded px-2 py-1.5">
                "{q.length > 80 ? q.slice(0, 80) + '...' : q}"
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Main KnowledgeGraph ───────────────────────────────────────────────────────

function KnowledgeGraph({ userId, refreshTrigger }) {
  const [graphData,     setGraphData]     = useState(null);
  const [isLoading,     setIsLoading]     = useState(true);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [activeView,    setActiveView]    = useState('bubbles'); // 'bubbles' | 'path'

  useEffect(() => {
    loadGraph();
  }, [userId, refreshTrigger]);

  async function loadGraph() {
    try {
      const res  = await fetch(`http://localhost:8000/api/knowledge/${userId}`);
      const data = await res.json();
      setGraphData(data);
    } catch (err) {
      console.error('Knowledge graph load failed:', err);
    } finally {
      setIsLoading(false);
    }
  }

  // Build learning path connections from known topics
  function buildPathConnections(topics) {
    const knownTopics = new Set(topics.map(t => t.topic));
    const connections = [];

    for (const [from, to] of Object.entries(LEARNING_PATH)) {
      if (knownTopics.has(from)) {
        connections.push({ from, to, known: knownTopics.has(to) });
      }
    }
    return connections;
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6
                      flex items-center justify-center h-64">
        <p className="text-sm text-gray-400">Loading knowledge graph...</p>
      </div>
    );
  }

  const topics      = graphData?.topics?.filter(t => t.topic !== 'general') || [];
  const connections = buildPathConnections(topics);
  const isEmpty     = topics.length === 0;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-semibold text-gray-700">🗺️ Knowledge Graph</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {topics.length} topics • {graphData?.total_sessions || 0} total sessions
          </p>
        </div>

        {/* View Toggle */}
        {!isEmpty && (
          <div className="flex bg-gray-100 rounded-lg p-0.5">
            {['bubbles', 'path'].map(view => (
              <button
                key={view}
                onClick={() => setActiveView(view)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all
                  ${activeView === view
                    ? 'bg-white text-indigo-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                  }`}
              >
                {view === 'bubbles' ? '⚪ Map' : '→ Path'}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Empty State */}
      {isEmpty && (
        <div className="text-center py-12">
          <p className="text-3xl mb-2">🌱</p>
          <p className="text-sm text-gray-500 font-medium">Your knowledge map is empty</p>
          <p className="text-xs text-gray-400 mt-1">
            Start learning — topics will appear here automatically
          </p>
        </div>
      )}

      {/* Bubble View */}
      {!isEmpty && activeView === 'bubbles' && (
        <>
          <div className="flex flex-wrap gap-4 justify-center py-6 min-h-[140px]
                          bg-gray-50 rounded-xl px-4">
            {topics.map(topic => (
              <TopicBubble
                key={topic.topic}
                topic={topic}
                isSelected={selectedTopic?.topic === topic.topic}
                onClick={t => setSelectedTopic(prev =>
                  prev?.topic === t.topic ? null : t
                )}
              />
            ))}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mt-4 justify-center flex-wrap">
            {[
              { color: '#e5e7eb', label: 'New (1-2×)' },
              { color: '#eab308', label: 'Learning (3-5×)' },
              { color: '#3b82f6', label: 'Growing (6-9×)' },
              { color: '#22c55e', label: 'Strong (10×+)' },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full border"
                     style={{ backgroundColor: color }} />
                <span className="text-xs text-gray-400">{label}</span>
              </div>
            ))}
          </div>

          {/* Suggested Next */}
          {graphData?.suggested_next && (
            <div className="mt-4 bg-indigo-50 rounded-lg px-4 py-3 flex items-center gap-3">
              <span className="text-lg">💡</span>
              <div>
                <p className="text-xs font-semibold text-indigo-700">Suggested next</p>
                <p className="text-sm text-indigo-600">
                  Try asking about <strong>{graphData.suggested_next}</strong>
                </p>
              </div>
            </div>
          )}
        </>
      )}

      {/* Path View */}
      {!isEmpty && activeView === 'path' && (
        <div className="py-2">
          <p className="text-xs text-gray-400 mb-3">
            Your explored connections — greyed topics are suggested next steps.
          </p>
          {connections.length > 0 ? (
            <div className="grid grid-cols-2 gap-2">
              {connections.map(({ from, to, known }, i) => (
                <PathConnection key={i} from={from} to={to} known={known} />
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-400 text-center py-4">
              Learn more topics to see connections appear here.
            </p>
          )}

          {/* Full Path Legend */}
          <div className="mt-4 bg-gray-50 rounded-lg p-3">
            <p className="text-xs font-semibold text-gray-500 mb-2">📍 Full Learning Path</p>
            <div className="flex flex-wrap gap-1 text-xs">
              {Object.entries(LEARNING_PATH).slice(0, 8).map(([from, to], i) => {
                const isKnown = topics.some(t => t.topic === from);
                return (
                  <span key={i}
                    className={`px-2 py-0.5 rounded-full border text-xs
                      ${isKnown
                        ? 'bg-indigo-100 border-indigo-200 text-indigo-600'
                        : 'bg-gray-100 border-gray-200 text-gray-400'
                      }`}
                  >
                    {from}
                  </span>
                );
              })}
              <span className="text-gray-300 self-center">→ ...</span>
            </div>
          </div>
        </div>
      )}

      {/* Topic Detail Panel */}
      {selectedTopic && activeView === 'bubbles' && (
        <TopicDetailPanel
          topic={selectedTopic}
          userId={userId}
          onClose={() => setSelectedTopic(null)}
        />
      )}
    </div>
  );
}

export default KnowledgeGraph;
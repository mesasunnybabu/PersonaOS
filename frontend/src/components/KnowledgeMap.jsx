// frontend/src/components/KnowledgeMap.jsx
//
// PURPOSE: Visual representation of the user's knowledge graph.
// Shows topics as bubbles — bigger = more explored, greener = more confident.
// Updates after every chat message.

import React, { useState, useEffect } from 'react';

// ── Topic Color Helper ────────────────────────────────────────────────────────
// Maps confidence score (0.0 → 1.0) to a color

function getTopicColor(confidence) {
  if (confidence >= 0.8) return { bg: 'bg-green-500',  text: 'text-white',      border: 'border-green-600',  label: 'Strong' };
  if (confidence >= 0.5) return { bg: 'bg-blue-400',   text: 'text-white',      border: 'border-blue-500',   label: 'Growing' };
  if (confidence >= 0.2) return { bg: 'bg-yellow-300', text: 'text-yellow-900', border: 'border-yellow-400', label: 'Exploring' };
  return                         { bg: 'bg-gray-100',   text: 'text-gray-600',   border: 'border-gray-200',   label: 'New' };
}

// Maps encounter count to bubble size (Tailwind classes)
function getBubbleSize(count) {
  if (count >= 10) return 'w-20 h-20 text-sm';
  if (count >= 5)  return 'w-16 h-16 text-xs';
  if (count >= 2)  return 'w-14 h-14 text-xs';
  return                  'w-12 h-12 text-xs';
}

// ── Topic Bubble ──────────────────────────────────────────────────────────────

function TopicBubble({ topic, onClick, isSelected }) {
  const colors = getTopicColor(topic.confidence_score);
  const size   = getBubbleSize(topic.encounter_count);

  return (
    <button
      onClick={() => onClick(topic)}
      className={`
        ${size} ${colors.bg} ${colors.text} ${colors.border}
        rounded-full border-2 flex flex-col items-center justify-center
        transition-all duration-200 hover:scale-110 flex-shrink-0
        ${isSelected ? 'ring-4 ring-indigo-400 ring-offset-2 scale-110' : ''}
        shadow-sm hover:shadow-md
      `}
      title={`${topic.topic}: ${topic.encounter_count} sessions`}
    >
      <span className="font-bold leading-tight text-center px-1 break-all">
        {topic.topic}
      </span>
      <span className="opacity-75 text-xs">
        {topic.encounter_count}×
      </span>
    </button>
  );
}

// ── Detail Panel ──────────────────────────────────────────────────────────────

function TopicDetailPanel({ topic, userId, onClose }) {
  const [detail, setDetail]   = useState(null);
  const [loading, setLoading] = useState(true);
  const colors = getTopicColor(topic.confidence_score);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_API_URL}/api/knowledge/${userId}/topic/${topic.topic}`)
      .then(r => r.json())
      .then(d => setDetail(d))
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [topic, userId]);

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 mt-3">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold px-2 py-1 rounded-full ${colors.bg} ${colors.text}`}>
            {topic.topic}
          </span>
          <span className="text-xs text-gray-500">{colors.label}</span>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
      </div>

      {/* Confidence Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Confidence</span>
          <span>{Math.round(topic.confidence_score * 100)}%</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all duration-500"
            style={{ width: `${topic.confidence_score * 100}%` }}
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">
          {topic.encounter_count} sessions • {10 - Math.min(topic.encounter_count, 10)} more to master
        </p>
      </div>

      {/* Recent Questions */}
      {loading ? (
        <p className="text-xs text-gray-400">Loading recent questions...</p>
      ) : detail?.recent_questions?.length > 0 ? (
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
      ) : null}
    </div>
  );
}

// ── Main KnowledgeMap ─────────────────────────────────────────────────────────

function KnowledgeMap({ userId, refreshTrigger }) {
  const [graphData,      setGraphData]      = useState(null);
  const [isLoading,      setIsLoading]      = useState(true);
  const [selectedTopic,  setSelectedTopic]  = useState(null);

  // Reload graph whenever refreshTrigger changes (after each chat message)
  useEffect(() => {
    loadGraph();
  }, [userId, refreshTrigger]);

  async function loadGraph() {
    try {
      const res  = await fetch(`${process.env.REACT_APP_API_URL}/api/knowledge/${userId}`);
      const data = await res.json();
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load knowledge graph:', err);
    } finally {
      setIsLoading(false);
    }
  }

  function handleTopicClick(topic) {
    setSelectedTopic(prev =>
      prev?.topic === topic.topic ? null : topic
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-semibold text-gray-700">🗺️ Knowledge Map</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Topics grow as you learn. Click any bubble for details.
          </p>
        </div>
        {graphData && (
          <div className="text-right">
            <p className="text-xs text-gray-400">{graphData.total_topics} topics explored</p>
            <p className="text-xs text-gray-400">{graphData.total_sessions} total sessions</p>
          </div>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <p className="text-sm text-gray-400">Loading your knowledge map...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && (!graphData || graphData.topics.length === 0) && (
        <div className="text-center py-8 px-4">
          <p className="text-3xl mb-2">🌱</p>
          <p className="text-sm text-gray-500 font-medium">Your knowledge map is empty</p>
          <p className="text-xs text-gray-400 mt-1">
            Start a conversation — topics will appear here as you learn.
          </p>
        </div>
      )}

      {/* Topic Bubbles */}
      {!isLoading && graphData && graphData.topics.length > 0 && (
        <>
          <div className="flex flex-wrap gap-3 justify-center py-4 min-h-[120px] bg-gray-50 rounded-xl px-3">
            {graphData.topics.map(topic => (
              <TopicBubble
                key={topic.topic}
                topic={topic}
                onClick={handleTopicClick}
                isSelected={selectedTopic?.topic === topic.topic}
              />
            ))}
          </div>

          {/* Topic Detail Panel */}
          {selectedTopic && (
            <TopicDetailPanel
              topic={selectedTopic}
              userId={userId}
              onClose={() => setSelectedTopic(null)}
            />
          )}

          {/* Legend */}
          <div className="flex items-center gap-4 mt-4 justify-center flex-wrap">
            {[
              { color: 'bg-gray-100 border-gray-200',    label: 'New (1-2×)' },
              { color: 'bg-yellow-300 border-yellow-400', label: 'Exploring (3-5×)' },
              { color: 'bg-blue-400 border-blue-500',     label: 'Growing (6-9×)' },
              { color: 'bg-green-500 border-green-600',   label: 'Strong (10×+)' },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-1.5">
                <div className={`w-3 h-3 rounded-full border ${color}`} />
                <span className="text-xs text-gray-500">{label}</span>
              </div>
            ))}
          </div>

          {/* Suggested Next Topic */}
          {graphData.suggested_next && (
            <div className="mt-4 bg-indigo-50 rounded-lg px-4 py-3 flex items-center gap-3">
              <span className="text-lg">💡</span>
              <div>
                <p className="text-xs font-semibold text-indigo-700">Suggested next topic</p>
                <p className="text-sm text-indigo-600">
                  Try asking about <strong>{graphData.suggested_next}</strong> to continue your learning path.
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default KnowledgeMap;
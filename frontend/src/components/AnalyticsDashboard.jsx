// frontend/src/components/AnalyticsDashboard.jsx
//
// Analytics tab content.
// Uses Recharts (already in your project) for lightweight SVG charts.

import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadialBarChart, RadialBar, Cell
} from 'recharts';

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, sub, color }) {
  const colorMap = {
    indigo: 'bg-indigo-50 border-indigo-100',
    green:  'bg-green-50  border-green-100',
    orange: 'bg-orange-50 border-orange-100',
    purple: 'bg-purple-50 border-purple-100',
    blue:   'bg-blue-50   border-blue-100',
  };
  const textMap = {
    indigo: 'text-indigo-600',
    green:  'text-green-600',
    orange: 'text-orange-600',
    purple: 'text-purple-600',
    blue:   'text-blue-600',
  };

  return (
    <div className={`rounded-xl border p-4 ${colorMap[color] || colorMap.indigo}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 mb-1">{label}</p>
          <p className={`text-2xl font-bold ${textMap[color] || textMap.indigo}`}>{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  );
}

// ── Custom Tooltip for Charts ─────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-white border border-gray-100 shadow-md rounded-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
}

// ── Confidence Ring ───────────────────────────────────────────────────────────
// Small radial bar showing confidence for a topic

function ConfidenceRing({ score, topic }) {
  const pct  = Math.round(score * 100);
  //const data = [{ value: pct }, { value: 100 - pct }];

  const color =
    pct >= 80 ? '#22c55e' :
    pct >= 50 ? '#3b82f6' :
    pct >= 20 ? '#eab308' : '#d1d5db';

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-14 h-14">
        <RadialBarChart
          width={56} height={56}
          cx={28} cy={28}
          innerRadius={18} outerRadius={26}
          startAngle={90} endAngle={-270}
          data={[{ value: pct, fill: color }]}
        >
          <RadialBar dataKey="value" cornerRadius={4} background={{ fill: '#f3f4f6' }} />
        </RadialBarChart>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-bold text-gray-700">{pct}%</span>
        </div>
      </div>
      <span className="text-xs text-gray-500 text-center leading-tight">{topic}</span>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────

function EmptyState({ icon, message, sub }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <span className="text-4xl mb-3">{icon}</span>
      <p className="text-sm font-medium text-gray-500">{message}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

// ── Main AnalyticsDashboard ───────────────────────────────────────────────────

function AnalyticsDashboard({ analytics }) {
  if (!analytics) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-400 text-sm">Loading analytics...</p>
      </div>
    );
  }

  const hasTopics = (analytics.topic_distribution || []).length > 0;
  const hasQuizzes = (analytics.quiz_performance || []).length > 0;

  // Prepare chart data — sort topics by sessions descending
  const topicChartData = [...analytics.topic_distribution]
    .sort((a, b) => b.sessions - a.sessions)
    .slice(0, 8)    // Show max 8 topics to keep chart readable
    .map(t => ({
      name:       t.topic,
      Sessions:   t.sessions,
      Confidence: Math.round(t.confidence * 100),
    }));

  const quizChartData = analytics.quiz_performance.map(q => ({
    name:     q.topic,
    Accuracy: q.accuracy,
    Total:    q.total,
  }));

  return (
    <div className="space-y-6">

      {/* ── Stat Cards Row ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon="💬" color="indigo"
          label="Total Sessions"
          value={analytics.total_sessions}
          sub={`${analytics.days_since_start} days learning`}
        />
        <StatCard
          icon="🗺️" color="blue"
          label="Topics Explored"
          value={analytics.total_topics}
          sub={analytics.most_active_topic ? `Most: ${analytics.most_active_topic}` : 'Start chatting!'}
        />
        <StatCard
          icon="🔥" color="orange"
          label="Current Streak"
          value={`${analytics.current_streak}d`}
          sub={`Best: ${analytics.longest_streak} days`}
        />
        <StatCard
          icon="📝" color="green"
          label="Quiz Accuracy"
          value={analytics.quiz_total > 0 ? `${analytics.quiz_accuracy}%` : '—'}
          sub={analytics.quiz_total > 0
            ? `${analytics.quiz_correct}/${analytics.quiz_total} correct`
            : 'No quizzes yet'
          }
        />
      </div>

      {/* ── Topic Sessions Bar Chart ── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-700">📊 Topic Activity</h3>
          <p className="text-xs text-gray-400">Sessions per topic</p>
        </div>

        {hasTopics ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={topicChartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11, fill: '#6b7280' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#6b7280' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="Sessions" fill="#6366f1" radius={[4, 4, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyState
            icon="📊"
            message="No topic data yet"
            sub="Start a conversation to see your activity chart"
          />
        )}
      </div>

      {/* ── Confidence Rings Row ── */}
      {hasTopics && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-700">🎯 Confidence by Topic</h3>
            <p className="text-xs text-gray-400">10 sessions = 100%</p>
          </div>
          <div className="flex flex-wrap gap-6 justify-center py-2">
            {analytics.topic_distribution
              .filter(t => t.topic !== 'general')
              .map(t => (
                <ConfidenceRing
                  key={t.topic}
                  topic={t.topic}
                  score={t.confidence}
                />
              ))
            }
          </div>
        </div>
      )}

      {/* ── Quiz Performance Bar Chart ── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-700">📝 Quiz Performance</h3>
          <p className="text-xs text-gray-400">Accuracy % per topic</p>
        </div>

        {hasQuizzes ? (
          <>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={quizChartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="Accuracy" radius={[4, 4, 0, 0]} maxBarSize={40}>
                  {quizChartData.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={
                        entry.Accuracy >= 80 ? '#22c55e' :
                        entry.Accuracy >= 50 ? '#3b82f6' : '#ef4444'
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            {/* Weakest topic callout */}
            {analytics.weakest_topic && (
              <div className="mt-3 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
                <p className="text-xs text-amber-700">
                  💡 <strong>{analytics.weakest_topic}</strong> has your lowest quiz score.
                  Try asking more questions about it to build confidence.
                </p>
              </div>
            )}
          </>
        ) : (
          <EmptyState
            icon="📝"
            message="No quiz data yet"
            sub="Quizzes appear every 3rd session on a topic"
          />
        )}
      </div>

      {/* ── Learning Summary ── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
        <h3 className="font-semibold text-gray-700 mb-3">📋 Learning Summary</h3>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-400 mb-1">Most Active Topic</p>
            <p className="font-semibold text-gray-700">
              {analytics.most_active_topic || 'None yet'}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-400 mb-1">Needs Practice</p>
            <p className="font-semibold text-gray-700">
              {analytics.weakest_topic || 'None yet'}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-400 mb-1">Quizzes Taken</p>
            <p className="font-semibold text-gray-700">{analytics.quiz_total}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-400 mb-1">Longest Streak</p>
            <p className="font-semibold text-gray-700">{analytics.longest_streak} days 🔥</p>
          </div>
        </div>
      </div>

    </div>
  );
}

export default AnalyticsDashboard;
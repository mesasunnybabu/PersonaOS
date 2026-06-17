// frontend/src/components/Sidebar.jsx
//
// Left sidebar: profile card, quick stats, review reminder.
// Always visible regardless of which tab is active.

import React from 'react';
import ReviewReminder from './ReviewReminder';

const levelConfig = {
  beginner:     { color: 'bg-green-100 text-green-700',   icon: '🌱', label: 'Beginner' },
  intermediate: { color: 'bg-blue-100 text-blue-700',     icon: '🌿', label: 'Intermediate' },
  advanced:     { color: 'bg-purple-100 text-purple-700', icon: '🌳', label: 'Advanced' },
};

// ── Stat Row ──────────────────────────────────────────────────────────────────

function StatRow({ icon, label, value, highlight }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
      <div className="flex items-center gap-2">
        <span className="text-sm">{icon}</span>
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <span className={`text-sm font-semibold ${highlight ? 'text-indigo-600' : 'text-gray-700'}`}>
        {value}
      </span>
    </div>
  );
}

// ── Main Sidebar ──────────────────────────────────────────────────────────────

function Sidebar({ profile, analytics, onReviewTopic, onLogout }) {
  const level = levelConfig[profile.experience_level] || levelConfig.beginner;

  return (
    <aside className="flex flex-col gap-4 w-64 flex-shrink-0">

      {/* Profile Card */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center
                          text-xl font-bold text-indigo-600 flex-shrink-0">
            {profile.name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <h2 className="font-bold text-gray-800 truncate">{profile.name}</h2>
            <p className="text-xs text-gray-400 truncate">{profile.background}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-3">
          <span className={`text-xs font-semibold px-2 py-1 rounded-full ${level.color}`}>
            {level.icon} {level.label}
          </span>
          <span className="bg-gray-100 text-gray-600 text-xs font-mono px-2 py-1 rounded">
            {profile.preferred_language}
          </span>
        </div>

        {profile.learning_goals && (
          <div className="bg-indigo-50 rounded-lg px-3 py-2 mb-3">
            <p className="text-xs text-indigo-600 font-semibold mb-0.5">🎯 Goals</p>
            <p className="text-xs text-gray-600 line-clamp-2">{profile.learning_goals}</p>
          </div>
        )}

        <button
          onClick={onLogout}
          className="w-full text-xs text-gray-400 hover:text-red-500 transition-colors text-center py-1"
        >
          Switch Profile
        </button>
      </div>

      {/* Quick Stats */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Quick Stats
        </h3>

        {analytics ? (
          <div>
            <StatRow icon="💬" label="Sessions"    value={analytics.total_sessions} />
            <StatRow icon="🗺️" label="Topics"      value={analytics.total_topics} />
            <StatRow
              icon="🔥"
              label="Streak"
              value={`${analytics.current_streak} day${analytics.current_streak !== 1 ? 's' : ''}`}
              highlight={analytics.current_streak >= 3}
            />
            <StatRow
              icon="📝"
              label="Quiz Score"
              value={analytics.quiz_total > 0 ? `${analytics.quiz_accuracy}%` : '—'}
              highlight={analytics.quiz_accuracy >= 70}
            />
            <StatRow icon="📅" label="Learning for" value={`${analytics.days_since_start}d`} />
          </div>
        ) : (
          <p className="text-xs text-gray-400 text-center py-2">Loading stats...</p>
        )}
      </div>

      {/* Streak Banner */}
      {analytics && analytics.current_streak >= 2 && (
        <div className="bg-gradient-to-br from-orange-50 to-yellow-50 border border-orange-200
                        rounded-2xl p-4 text-center">
          <p className="text-2xl mb-1">🔥</p>
          <p className="text-sm font-bold text-orange-700">
            {analytics.current_streak} Day Streak!
          </p>
          <p className="text-xs text-orange-500 mt-0.5">
            Best: {analytics.longest_streak} days
          </p>
        </div>
      )}

      {/* Review Reminder */}
      <ReviewReminder userId={profile.id} onReviewTopic={onReviewTopic} />

    </aside>
  );
}

export default Sidebar;
// frontend/src/components/Dashboard.jsx
// Phase 6 Final — Tabbed cognitive UI

import React, { useState, useEffect, useRef } from 'react';
import Sidebar             from './Sidebar';
import ChatInterface       from './ChatInterface';
import AnalyticsDashboard  from './AnalyticsDashboard';
import KnowledgeGraph      from './KnowledgeGraph';

// ── Tab Definition ────────────────────────────────────────────────────────────

const TABS = [
  { id: 'chat',      label: '💬 Chat',      desc: 'Ask anything' },
  { id: 'analytics', label: '📊 Analytics', desc: 'Your progress' },
  { id: 'knowledge', label: '🗺️ Knowledge', desc: 'Topic map' },
];

// ── Main Dashboard ────────────────────────────────────────────────────────────

function Dashboard({ profile, onLogout }) {
  const [activeTab,        setActiveTab]        = useState('chat');
  const [analytics,        setAnalytics]        = useState(null);
  const [knowledgeRefresh, setKnowledgeRefresh] = useState(0);
  const [showLogoutModal,  setShowLogoutModal]  = useState(false);
  const sendMessageRef = useRef(null);

  // Load analytics on mount + after each message
  useEffect(() => {
    loadAnalytics();
  }, [knowledgeRefresh]);

  async function loadAnalytics() {
    try {
      const res  = await fetch(`${process.env.REACT_APP_API_URL}/api/analytics/${profile.id}`);
      const data = await res.json();
      setAnalytics(data);
    } catch (err) {
      console.error('Analytics load failed:', err);
    }
  }

  function handleNewMessage() {
    setKnowledgeRefresh(prev => prev + 1);
  }

  // Called by ReviewReminder — sends a review message via ChatInterface
  function handleReviewTopic(message) {
    setActiveTab('chat');
    setTimeout(() => {
      if (sendMessageRef.current) sendMessageRef.current(message);
    }, 100);
  }

  return (
    <div className="min-h-screen bg-gray-50">

      {/* ── Header ── */}
      <header className="bg-indigo-700 text-white px-6 py-3 shadow-md">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🧠</span>
            <div>
              <h1 className="text-lg font-bold leading-tight">PersonaOS</h1>
              <p className="text-indigo-300 text-xs">Adaptive AI Coding Tutor</p>
            </div>
          </div>

          {/* Tab Navigation in Header */}
          <div className="flex bg-indigo-800 rounded-xl p-1 gap-1">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all
                  ${activeTab === tab.id
                    ? 'bg-white text-indigo-700 shadow-sm'
                    : 'text-indigo-200 hover:text-white hover:bg-indigo-700'
                  }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Streak + User */}
          <div className="flex items-center gap-3">
            {analytics?.current_streak >= 1 && (
              <div className="flex items-center gap-1 bg-indigo-600 px-3 py-1 rounded-full">
                <span className="text-sm">🔥</span>
                <span className="text-xs font-semibold text-orange-200">
                  {analytics.current_streak} day streak
                </span>
              </div>
            )}
            <span className="text-indigo-200 text-sm hidden lg:block">
              {profile.name}
            </span>
          </div>
        </div>
      </header>

      {/* ── Logout Modal ── */}
      {showLogoutModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full">
            <h3 className="font-bold text-gray-800 mb-2">Switch Profile?</h3>
            <p className="text-sm text-gray-500 mb-5">
              Clears your session. All data stays in the database.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowLogoutModal(false)}
                className="flex-1 border border-gray-200 rounded-lg py-2
                           text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={onLogout}
                className="flex-1 bg-red-500 hover:bg-red-600 text-white
                           rounded-lg py-2 text-sm font-medium"
              >
                Yes, Switch
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Main Layout ── */}
      <div className="max-w-7xl mx-auto px-4 py-6 flex gap-5">

        {/* Sidebar — always visible */}
        <Sidebar
          profile={profile}
          analytics={analytics}
          onReviewTopic={handleReviewTopic}
          onLogout={() => setShowLogoutModal(true)}
        />

        {/* Main Content Area */}
        <main className="flex-1 min-w-0">

          {/* TAB 1 — Chat */}
          {activeTab === 'chat' && (
            <ChatInterface
              profile={profile}
              onMessageSent={handleNewMessage}
              onSendRef={fn => { sendMessageRef.current = fn; }}
            />
          )}

          {/* TAB 2 — Analytics */}
          {activeTab === 'analytics' && (
            <AnalyticsDashboard analytics={analytics} />
          )}

          {/* TAB 3 — Knowledge Graph */}
          {activeTab === 'knowledge' && (
            <KnowledgeGraph
              userId={profile.id}
              refreshTrigger={knowledgeRefresh}
            />
          )}

        </main>
      </div>
    </div>
  );
}

export default Dashboard;
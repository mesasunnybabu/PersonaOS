// frontend/src/components/ChatInterface.jsx

import React, { useState, useEffect, useRef } from 'react';
import FollowUpChips from './FollowUpChips';
import QuizCard from './QuizCard';

function renderMessage(text) {
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    if (part.startsWith('```')) {
      const lines = part.slice(3, -3).split('\n');
      const lang  = lines[0].trim() || 'code';
      const code  = lines.slice(1).join('\n');
      return (
        <div key={i} className="my-3">
          <div className="bg-gray-800 text-gray-300 text-xs px-3 py-1 rounded-t-lg font-mono">
            {lang}
          </div>
          <pre className="bg-gray-900 text-green-300 text-sm px-4 py-3 rounded-b-lg
                          overflow-x-auto font-mono whitespace-pre-wrap">
            {code}
          </pre>
        </div>
      );
    }
    return <span key={i} className="whitespace-pre-wrap">{part}</span>;
  });
}

function MessageBubble({ message, onFollowUpSelect, isLoading }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center
                        text-white text-sm font-bold mr-2 flex-shrink-0 mt-1">
          AI
        </div>
      )}

      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>

        {/* Memory + Topic indicators */}
        {!isUser && (message.memoriesUsed?.length > 0 || message.topic) && (
          <div className="flex items-center gap-2 text-xs mb-1 ml-1">
            {message.memoriesUsed?.length > 0 && (
              <span className="text-indigo-500">
                🧠 {message.memoriesUsed.length} memory retrieved
              </span>
            )}
            {message.topic && message.topic !== 'general' && (
              <span className="bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded-full">
                {message.topic}
              </span>
            )}
          </div>
        )}

        {/* Message bubble */}
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed
          ${isUser
            ? 'bg-indigo-600 text-white rounded-tr-sm'
            : 'bg-white border border-gray-100 shadow-sm text-gray-800 rounded-tl-sm'
          }`}
        >
          {isUser ? message.content : renderMessage(message.content)}
        </div>

        <span className="text-xs text-gray-400 mt-1 mx-1">{message.timestamp}</span>

        {/* Follow-up chips — only on AI messages */}
        {!isUser && message.followUps?.length > 0 && (
          <FollowUpChips
            suggestions={message.followUps}
            onSelect={onFollowUpSelect}
            disabled={isLoading}
          />
        )}

        {/* Quiz card — only on AI messages */}
        {!isUser && message.quiz && (
          <QuizCard quiz={message.quiz} />
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center
                        text-gray-600 text-sm font-bold ml-2 flex-shrink-0 mt-1">
          U
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center
                      text-white text-sm font-bold mr-2 flex-shrink-0">
        AI
      </div>
      <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map(i => (
            <div key={i}
              className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function ChatInterface({ profile, onMessageSent, onSendRef }) {
  const [messages,         setMessages]         = useState([]);
  const [input,            setInput]            = useState('');
  const [isLoading,        setIsLoading]        = useState(false);
  const [memoryCount,      setMemoryCount]      = useState(0);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  const bottomRef = useRef(null);

useEffect(() => {
    loadHistory();
    loadMemoryStats();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (onSendRef) onSendRef((msg) => sendMessage(msg));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  async function loadHistory() {
    try {
      const res  = await fetch(`${process.env.REACT_APP_API_URL}/api/chat/history/${profile.id}`);
      const data = await res.json();

      const historyMessages = [];
      for (const conv of data.conversations) {
        historyMessages.push({
          role:      'user',
          content:   conv.user_message,
          timestamp: new Date(conv.created_at).toLocaleTimeString(),
          id:        `user-${conv.id}`
        });
        historyMessages.push({
          role:         'ai',
          content:      conv.ai_response,
          timestamp:    new Date(conv.created_at).toLocaleTimeString(),
          memoriesUsed: [],
          topic:        conv.topic,
          followUps:    [],
          quiz:         null,
          id:           `ai-${conv.id}`
        });
      }

      if (historyMessages.length === 0) {
        historyMessages.push({
          role:      'ai',
          content:   `Hi ${profile.name}! 👋 I'm your PersonaOS tutor.\n\nI'm at **${profile.experience_level}** level with **${profile.preferred_language}**. I remember everything we discuss and adapt to your knowledge level.\n\nWhat would you like to learn today?`,
          timestamp: 'now',
          memoriesUsed: [],
          followUps: [],
          quiz: null,
          id: 'welcome'
        });
      }

      setMessages(historyMessages);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }

  async function loadMemoryStats() {
    try {
      const res  = await fetch(`${process.env.REACT_APP_API_URL}/api/memory/stats/${profile.id}`);
      const data = await res.json();
      setMemoryCount(data.vectors_stored);
    } catch (err) {
      console.error('Failed to load memory stats:', err);
    }
  }

  async function sendMessage(messageText = null) {
    const trimmed = (messageText || input).trim();
    if (!trimmed || isLoading) return;

    const userMsg = {
      role:      'user',
      content:   trimmed,
      timestamp: new Date().toLocaleTimeString(),
      id:        `user-${Date.now()}`
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch(`${process.env.REACT_APP_API_URL}/api/chat`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ user_id: profile.id, message: trimmed })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Chat failed');
      }

      const data = await res.json();

      const aiMsg = {
        role:         'ai',
        content:      data.ai_response,
        timestamp:    new Date().toLocaleTimeString(),
        memoriesUsed: data.memories_used,
        topic:        data.topic,
        followUps:    data.follow_ups || [],
        quiz:         data.quiz || null,
        id:           `ai-${Date.now()}`
      };
      setMessages(prev => [...prev, aiMsg]);
      setMemoryCount(prev => prev + 1);
      if (onMessageSent) onMessageSent();

    } catch (err) {
      setMessages(prev => [...prev, {
        role:      'ai',
        content:   `⚠️ Error: ${err.message}`,
        timestamp: new Date().toLocaleTimeString(),
        memoriesUsed: [],
        followUps: [],
        quiz: null,
        id:        `err-${Date.now()}`
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm flex flex-col"
         style={{ height: '600px' }}>

      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
          <span className="font-semibold text-gray-700 text-sm">AI Tutor</span>
          <span className="text-xs text-gray-400">• Adaptive Mode</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-indigo-500 bg-indigo-50 px-2 py-1 rounded-full">
          <span>🧠</span>
          <span>{memoryCount} {memoryCount === 1 ? 'memory' : 'memories'}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {isLoadingHistory ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-400 text-sm">Loading conversation...</p>
          </div>
        ) : (
          <>
            {messages.map(msg => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onFollowUpSelect={(q) => sendMessage(q)}
                isLoading={isLoading}
              />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="px-4 py-4 border-t border-gray-100 flex-shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything... (Enter to send, Shift+Enter for new line)"
            rows={2}
            className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-sm
                       focus:outline-none focus:ring-2 focus:ring-indigo-400
                       resize-none transition-all"
          />
          <button
            onClick={() => sendMessage()}
            disabled={isLoading || !input.trim()}
            className={`px-4 py-3 rounded-xl font-semibold text-sm transition-all flex-shrink-0
              ${isLoading || !input.trim()
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white active:scale-95'
              }`}
          >
            {isLoading ? '⏳' : '➤'}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          Difficulty adapts automatically • Quizzes appear every 3 sessions
        </p>
      </div>
    </div>
  );
}

export default ChatInterface;
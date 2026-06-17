// frontend/src/components/OnboardingForm.jsx
//
// PURPOSE: Shown to first-time users. Collects their profile info
// and POSTs it to the backend.

import React, { useState } from 'react';

// ── Constants ─────────────────────────────────────────────────────────────────

const EXPERIENCE_LEVELS = [
  { value: 'beginner',     label: '🌱 Beginner',     desc: 'Just starting out' },
  { value: 'intermediate', label: '🌿 Intermediate',  desc: 'Know the basics, building projects' },
  { value: 'advanced',     label: '🌳 Advanced',      desc: 'Comfortable with complex systems' },
];

const LANGUAGES = ['Python', 'JavaScript', 'Java', 'C++', 'Rust', 'Go', 'Other'];

// ── Component ─────────────────────────────────────────────────────────────────

function OnboardingForm({ onComplete }) {
  // onComplete is a callback prop — when this form is done, it calls
  // onComplete(profileData) to tell App.jsx to switch to the Dashboard

  // ── Form State ─────────────────────────────────────────────────────────────
  // Each field in the form has its own piece of state
  const [formData, setFormData] = useState({
    name:               '',
    background:         '',
    experience_level:   '',
    learning_goals:     '',
    preferred_language: 'Python',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError]               = useState(null);

  // ── Handlers ───────────────────────────────────────────────────────────────

  // Generic change handler — works for all text inputs and selects
  // [e.target.name] is computed property syntax: it uses the input's
  // name attribute as the key to update in formData
  function handleChange(e) {
    setFormData(prev => ({
      ...prev,                          // Keep all existing fields
      [e.target.name]: e.target.value   // Update only the changed field
    }));
  }

  async function handleSubmit() {
    // Basic client-side validation before hitting the API
    if (!formData.name.trim()) {
      setError('Please enter your name.');
      return;
    }
    if (!formData.background.trim()) {
      setError('Please describe your background.');
      return;
    }
    if (!formData.experience_level) {
      setError('Please select your experience level.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',  // Tell FastAPI we're sending JSON
        },
        body: JSON.stringify(formData),         // Convert JS object → JSON string
      });

      if (!response.ok) {
        const errData = await response.json();
        // FastAPI puts error details in errData.detail
        throw new Error(errData.detail || 'Failed to create profile');
      }

      const profile = await response.json();

      // Save the profile ID to localStorage so we recognize this user on return
      localStorage.setItem('persona_user_id', profile.id.toString());

      // Tell App.jsx we're done — pass the full profile data up
      onComplete(profile);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50 flex items-center justify-center px-4 py-10">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-xl p-8">

        {/* Header */}
        <div className="mb-8 text-center">
          <div className="text-5xl mb-3">🧠</div>
          <h1 className="text-2xl font-bold text-gray-800">Welcome to PersonaOS</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Let's set up your learning profile. This helps me adapt to you.
          </p>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-400 text-red-700 p-3 rounded-md mb-5 text-sm">
            {error}
          </div>
        )}

        {/* Form Fields */}
        <div className="space-y-5">

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Your Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g. Arjun"
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent
                         transition-all"
            />
          </div>

          {/* Background */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Your Background <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              name="background"
              value={formData.background}
              onChange={handleChange}
              placeholder="e.g. M.Tech student, self-taught developer, CS undergrad..."
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent
                         transition-all"
            />
          </div>

          {/* Experience Level */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Experience Level <span className="text-red-400">*</span>
            </label>
            <div className="grid grid-cols-3 gap-2">
              {EXPERIENCE_LEVELS.map(({ value, label, desc }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, experience_level: value }))}
                  className={`border rounded-lg p-3 text-left transition-all
                    ${formData.experience_level === value
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                      : 'border-gray-200 hover:border-indigo-300 text-gray-600'
                    }`}
                >
                  <div className="font-medium text-sm">{label}</div>
                  <div className="text-xs mt-0.5 opacity-70">{desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Preferred Language */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Preferred Language
            </label>
            <select
              name="preferred_language"
              value={formData.preferred_language}
              onChange={handleChange}
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-400
                         bg-white transition-all"
            >
              {LANGUAGES.map(lang => (
                <option key={lang} value={lang}>{lang}</option>
              ))}
            </select>
          </div>

          {/* Learning Goals */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Learning Goals
              <span className="text-gray-400 font-normal ml-1">(optional)</span>
            </label>
            <textarea
              name="learning_goals"
              value={formData.learning_goals}
              onChange={handleChange}
              rows={3}
              placeholder="e.g. I want to build AI-powered apps, understand LLMs, and get an internship at a product company..."
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-400
                         resize-none transition-all"
            />
          </div>

        </div>

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className={`mt-6 w-full py-3 rounded-xl font-semibold text-white text-sm
            transition-all
            ${isSubmitting
              ? 'bg-indigo-300 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-700 active:scale-95'
            }`}
        >
          {isSubmitting ? '⏳ Creating your profile...' : '🚀 Start Learning'}
        </button>

        <p className="text-center text-xs text-gray-400 mt-4">
          Your profile is stored locally. You can update it anytime.
        </p>

      </div>
    </div>
  );
}

export default OnboardingForm;
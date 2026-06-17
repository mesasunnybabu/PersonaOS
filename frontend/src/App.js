// frontend/src/App.jsx
//
// PURPOSE: The root component. Acts as a controller — decides which
// screen to show based on whether the user has a profile or not.

import React, { useState, useEffect } from 'react';
import './App.css';
import OnboardingForm from './components/OnboardingForm';
import Dashboard from './components/Dashboard';

// The key we use to store the user's ID in localStorage
const STORAGE_KEY = 'persona_user_id';

function App() {
  // null    → we haven't checked yet (show loading)
  // false   → no profile found (show onboarding)
  // object  → profile loaded (show dashboard)
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // ── On Mount: Check for existing profile ───────────────────────────────────
  useEffect(() => {
    loadExistingProfile();
  }, []);

  async function loadExistingProfile() {
    const savedId = localStorage.getItem(STORAGE_KEY);

    if (!savedId) {
      // No saved ID — this is a first-time visitor
      setProfile(false);
      setIsLoading(false);
      return;
    }

    // We have an ID — try to fetch the profile from the backend
    try {
      const response = await fetch(`http://localhost:8000/api/profile/${savedId}`);

      if (!response.ok) {
        // Profile ID in localStorage but not in DB (e.g. DB was reset)
        // Clear the stale ID and show onboarding again
        localStorage.removeItem(STORAGE_KEY);
        setProfile(false);
      } else {
        const data = await response.json();
        setProfile(data);
      }
    } catch (error) {
      // Backend is down — still try to degrade gracefully
      console.error('Could not load profile:', error);
      setProfile(false);
    } finally {
      setIsLoading(false);
    }
  }

  // ── Called by OnboardingForm when profile is created ──────────────────────
  function handleOnboardingComplete(newProfile) {
    setProfile(newProfile);
  }

  // ── Called by Dashboard's "Switch Profile" button ─────────────────────────
  function handleLogout() {
    localStorage.removeItem(STORAGE_KEY);
    setProfile(false);
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  // Still checking localStorage / fetching profile
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-3 animate-pulse">🧠</div>
          <p className="text-gray-500 text-sm">Loading PersonaOS...</p>
        </div>
      </div>
    );
  }

  // No profile — show onboarding
  if (!profile) {
    return <OnboardingForm onComplete={handleOnboardingComplete} />;
  }

  // Profile loaded — show dashboard
  return <Dashboard profile={profile} onLogout={handleLogout} />;
}

export default App;
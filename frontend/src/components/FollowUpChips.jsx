// frontend/src/components/FollowUpChips.jsx
//
// Displays 3 clickable suggestion chips below an AI message.
// Clicking a chip sends it as the next message automatically.

import React from 'react';

function FollowUpChips({ suggestions, onSelect, disabled }) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="mt-3 ml-10">
      <p className="text-xs text-gray-400 mb-2">💡 Suggested next questions:</p>
      <div className="flex flex-col gap-1.5">
        {suggestions.map((suggestion, i) => (
          <button
            key={i}
            onClick={() => onSelect(suggestion)}
            disabled={disabled}
            className={`text-left text-xs px-3 py-2 rounded-lg border transition-all
              ${disabled
                ? 'border-gray-100 text-gray-300 cursor-not-allowed bg-gray-50'
                : 'border-indigo-200 text-indigo-600 bg-indigo-50 hover:bg-indigo-100 hover:border-indigo-300 active:scale-95'
              }`}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

export default FollowUpChips;
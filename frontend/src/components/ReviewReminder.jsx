// frontend/src/components/ReviewReminder.jsx
//
// Shows a banner when topics are due for spaced repetition review.
// Clicking a topic sends it as a chat message automatically.

import React, { useState, useEffect } from 'react';

function ReviewReminder({ userId, onReviewTopic }) {
  const [reviews,   setReviews]   = useState([]);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    fetchReviews();
  }, [userId]);

  async function fetchReviews() {
    try {
      const res  = await fetch(`${process.env.REACT_APP_API_URL}/api/reviews/${userId}`);
      const data = await res.json();
      setReviews(data.due_reviews || []);
    } catch (err) {
      console.error('Failed to fetch reviews:', err);
    }
  }

  if (dismissed || reviews.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg">🔔</span>
          <p className="text-sm font-semibold text-amber-800">
            {reviews.length} topic{reviews.length > 1 ? 's' : ''} ready for review
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-amber-400 hover:text-amber-600 text-lg leading-none"
        >
          ×
        </button>
      </div>

      <p className="text-xs text-amber-600 mb-3">
        Reviewing now helps you remember longer. Click a topic to start.
      </p>

      <div className="flex flex-wrap gap-2">
        {reviews.map(review => (
          <button
            key={review.topic}
            onClick={() => {
              onReviewTopic(`Can you quiz me on ${review.topic}?`);
              setDismissed(true);
            }}
            className="flex items-center gap-1.5 bg-amber-100 hover:bg-amber-200
                       border border-amber-300 text-amber-800 text-xs font-medium
                       px-3 py-1.5 rounded-full transition-all"
          >
            <span>{review.topic}</span>
            {review.days_overdue > 0 && (
              <span className="bg-red-400 text-white text-xs px-1.5 rounded-full">
                {review.days_overdue}d
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export default ReviewReminder;
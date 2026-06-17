// frontend/src/components/QuizCard.jsx
//
// Interactive multiple-choice quiz card.
// Appears after every 3rd encounter with a topic.

import React, { useState } from 'react';

function QuizCard({ quiz, onAnswer }) {
  const [selected,  setSelected]  = useState(null);   // "A", "B", "C", "D"
  const [result,    setResult]    = useState(null);   // {is_correct, explanation, correct_option}
  const [isLoading, setIsLoading] = useState(false);

  const options = [
    { key: 'A', text: quiz.option_a },
    { key: 'B', text: quiz.option_b },
    { key: 'C', text: quiz.option_c },
    { key: 'D', text: quiz.option_d },
  ];

  async function handleSelect(optionKey) {
    if (result || isLoading) return;   // Already answered

    setSelected(optionKey);
    setIsLoading(true);

    try {
      const res  = await fetch('${process.env.REACT_APP_API_URL}/api/quiz/answer', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          quiz_id:     quiz.quiz_id,
          user_answer: optionKey
        })
      });
      const data = await res.json();
      setResult(data);
      if (onAnswer) onAnswer(data);
    } catch (err) {
      console.error('Quiz answer failed:', err);
    } finally {
      setIsLoading(false);
    }
  }

  function getOptionStyle(key) {
    // Before answering
    if (!result) {
      return selected === key
        ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
        : 'border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 text-gray-700 cursor-pointer';
    }

    // After answering
    if (key === result.correct_option) {
      return 'border-green-400 bg-green-50 text-green-700';   // Correct answer
    }
    if (key === selected && !result.is_correct) {
      return 'border-red-400 bg-red-50 text-red-700';         // Wrong selection
    }
    return 'border-gray-100 text-gray-400';                    // Unselected
  }

  return (
    <div className="mt-4 ml-10 bg-white border border-indigo-100 rounded-xl shadow-sm p-4">

      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">📝</span>
        <span className="text-sm font-semibold text-indigo-700">Quick Check</span>
        <span className="text-xs bg-indigo-100 text-indigo-500 px-2 py-0.5 rounded-full">
          {quiz.topic}
        </span>
      </div>

      {/* Question */}
      <p className="text-sm text-gray-800 font-medium mb-3">{quiz.question}</p>

      {/* Options */}
      <div className="space-y-2">
        {options.map(({ key, text }) => (
          <button
            key={key}
            onClick={() => handleSelect(key)}
            disabled={!!result || isLoading}
            className={`w-full text-left flex items-start gap-2 px-3 py-2
              border rounded-lg text-sm transition-all ${getOptionStyle(key)}`}
          >
            <span className="font-bold flex-shrink-0 w-5">{key}.</span>
            <span>{text}</span>
          </button>
        ))}
      </div>

      {/* Result */}
      {result && (
        <div className={`mt-3 p-3 rounded-lg text-sm
          ${result.is_correct ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          <p className="font-semibold mb-1">
            {result.is_correct ? '✅ Correct!' : `❌ Not quite. Answer: ${result.correct_option}`}
          </p>
          <p className="text-xs opacity-80">{result.explanation}</p>
          <p className="text-xs mt-1 opacity-60">
            Confidence updated: {Math.round(result.new_confidence * 100)}%
          </p>
        </div>
      )}

      {isLoading && (
        <p className="text-xs text-gray-400 mt-2 text-center">Checking answer...</p>
      )}
    </div>
  );
}

export default QuizCard;
import { useEffect, useState } from 'react'

// Diverse pool of loading messages for varied user experience
const LOADING_MESSAGES = [
  "Thinking through your question...",
  "Processing request...",
  "Analyzing context...",
  "Searching through notes...",
  "Understanding your query...",
  "Gathering relevant information...",
  "Formulating response...",
  "Exploring connections...",
  "Evaluating options...",
  "Synthesizing information...",
  "Reviewing file context...",
  "Computing results...",
  "Building answer...",
  "Examining patterns...",
  "Connecting the dots...",
  "Parsing information...",
  "Generating response...",
  "Considering possibilities...",
  "Assessing data...",
  "Organizing thoughts...",
  "Crafting reply...",
  "Querying knowledge base...",
  "Refining answer...",
  "Piecing together details...",
  "Finalizing response...",
  "Preparing analysis...",
  "Working on it..."
]

export default function LoadingIndicator() {
  const [messageIndex, setMessageIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % LOADING_MESSAGES.length)
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div
      className="flex items-center gap-3 py-2"
      role="status"
      aria-live="polite"
      aria-label={LOADING_MESSAGES[messageIndex]}
    >
      {/* Animated shimmer dot */}
      <div className="shimmer-loading rounded-full w-2.5 h-2.5" />

      {/* Message container with shimmer background */}
      <div className="relative overflow-hidden rounded-2xl px-4 py-2 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border border-blue-200 dark:border-blue-800">
        {/* Shimmer overlay */}
        <div className="absolute inset-0 shimmer-loading opacity-50" />

        {/* Text content */}
        <span className="relative z-10 text-sm font-medium text-gray-700 dark:text-gray-300">
          {LOADING_MESSAGES[messageIndex]}
        </span>
      </div>
    </div>
  )
}


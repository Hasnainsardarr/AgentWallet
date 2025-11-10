import React from 'react'

export default function LoadingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="bg-defi-bg-light border border-defi-border rounded-xl px-4 py-3">
        <div className="flex space-x-2">
          <div className="w-2.5 h-2.5 bg-defi-lavender rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-2.5 h-2.5 bg-defi-lavender rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-2.5 h-2.5 bg-defi-lavender rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
      </div>
    </div>
  )
}


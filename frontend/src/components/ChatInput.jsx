import React, { useState } from 'react'

export default function ChatInput({ onSend, disabled }) {
  const [input, setInput] = useState('')
  
  const handleSubmit = (e) => {
    e.preventDefault()
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput('')
    }
  }
  
  return (
    <form onSubmit={handleSubmit} className="border-t border-defi-border/20 bg-defi-bg px-4 py-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 bg-defi-bg-light/50 border border-defi-border/30 rounded-2xl p-2 focus-within:border-defi-purple/50 transition-all duration-200">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
              }
            }}
            placeholder="Message ITP Wallet Agent..."
            disabled={disabled}
            rows={1}
            className="flex-1 px-3 py-2.5 bg-transparent text-defi-text placeholder-defi-text-dim/60 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed resize-none max-h-32 text-base"
            style={{ minHeight: '40px' }}
          />
          <button
            type="submit"
            disabled={disabled || !input.trim()}
            className="p-2.5 bg-defi-purple hover:bg-defi-purple-dark disabled:bg-defi-bg-lighter disabled:cursor-not-allowed rounded-xl transition-all duration-200 shrink-0"
          >
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-defi-text-dim/60 text-center mt-2">
          Press Enter to send, Shift + Enter for new line
        </p>
      </div>
    </form>
  )
}


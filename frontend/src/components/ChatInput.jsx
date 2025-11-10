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
    <form onSubmit={handleSubmit} className="border-t border-defi-border bg-defi-bg-light p-4">
      <div className="flex space-x-3 max-w-4xl mx-auto">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={disabled}
          className="flex-1 px-4 py-3 bg-defi-bg border border-defi-border rounded-lg text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-defi-purple focus:border-defi-purple disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        />
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="px-8 py-3 bg-defi-purple text-white rounded-lg hover:bg-defi-purple-dark disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium shadow-lg shadow-defi-purple/20 hover:shadow-defi-purple/30"
        >
          Send
        </button>
      </div>
    </form>
  )
}


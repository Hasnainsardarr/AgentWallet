import React from 'react'

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  
  const formatMessage = (text) => {
    const txHashRegex = /(0x[a-fA-F0-9]{64})/g
    const addressRegex = /\b(0x[a-fA-F0-9]{40})\b/g
    
    let formatted = text.replace(txHashRegex, (match) => {
      return `<a href="https://sepolia.basescan.org/tx/${match}" target="_blank" rel="noopener noreferrer" class="text-defi-lavender hover:text-defi-lavender-light underline">${match.slice(0, 10)}...${match.slice(-8)}</a>`
    })
    
    formatted = formatted.replace(addressRegex, (match) => {
      return `<code class="bg-defi-bg-lighter px-2 py-0.5 rounded text-sm text-defi-lavender border border-defi-border">${match.slice(0, 8)}...${match.slice(-6)}</code>`
    })
    
    return formatted
  }
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-xl px-4 py-3 ${
          isUser
            ? 'bg-defi-purple text-white shadow-lg shadow-defi-purple/20'
            : 'bg-defi-bg-light border border-defi-border text-defi-text'
        }`}
      >
        <div
          className="whitespace-pre-wrap break-words text-sm leading-relaxed"
          dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }}
        />
      </div>
    </div>
  )
}


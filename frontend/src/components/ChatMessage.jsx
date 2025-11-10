import React from 'react'

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  
  const formatMessage = (text) => {
    const txHashRegex = /(0x[a-fA-F0-9]{64})/g
    const addressRegex = /\b(0x[a-fA-F0-9]{40})\b/g
    
    let formatted = text.replace(txHashRegex, (match) => {
      return `<a href="https://sepolia.basescan.org/tx/${match}" target="_blank" rel="noopener noreferrer" class="text-defi-lavender hover:text-defi-lavender-light underline decoration-dotted underline-offset-2 transition-colors inline-flex items-center gap-1">
        ${match.slice(0, 10)}...${match.slice(-8)}
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
      </a>`
    })
    
    formatted = formatted.replace(addressRegex, (match) => {
      return `<code class="bg-defi-bg-lighter/80 px-2 py-0.5 rounded text-sm text-defi-lavender border border-defi-border/50 font-mono">${match.slice(0, 8)}...${match.slice(-6)}</code>`
    })
    
    return formatted
  }
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 group animate-in fade-in slide-in-from-bottom-2 duration-300`}>
      <div
        className={`max-w-[85%] sm:max-w-[80%] rounded-2xl px-4 py-3 relative overflow-hidden transition-all duration-200 ${
          isUser
            ? 'bg-gradient-to-br from-defi-purple to-defi-purple-dark text-white shadow-lg shadow-defi-purple/30 hover:shadow-glow-sm'
            : 'bg-gradient-to-br from-defi-bg-light to-defi-bg-lighter border border-defi-border/50 text-defi-text hover:border-defi-purple/30 shadow-lg'
        }`}
      >
        {/* Subtle shine effect on hover */}
        {isUser && (
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 -translate-x-full group-hover:translate-x-full animate-shimmer"></div>
        )}
        
        <div
          className="whitespace-pre-wrap break-words text-sm leading-relaxed relative z-10"
          dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }}
        />
      </div>
    </div>
  )
}


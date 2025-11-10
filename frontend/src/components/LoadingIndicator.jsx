import React from 'react'

export default function LoadingIndicator() {
  return (
    <div className="flex justify-start mb-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="bg-gradient-to-br from-defi-bg-light to-defi-bg-lighter border border-defi-border/50 rounded-2xl px-5 py-4 shadow-lg relative overflow-hidden">
        {/* Animated background pulse */}
        <div className="absolute inset-0 bg-gradient-to-r from-defi-purple/5 via-defi-lavender/5 to-defi-purple/5 animate-pulse"></div>
        
        <div className="flex items-center space-x-3 relative z-10">
          <div className="flex space-x-1.5">
            <div className="w-2.5 h-2.5 bg-gradient-to-br from-defi-purple to-defi-purple-light rounded-full animate-bounce shadow-glow-sm" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2.5 h-2.5 bg-gradient-to-br from-defi-purple-light to-defi-lavender rounded-full animate-bounce shadow-glow-sm" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2.5 h-2.5 bg-gradient-to-br from-defi-lavender to-defi-lavender-light rounded-full animate-bounce shadow-glow-sm" style={{ animationDelay: '300ms' }}></div>
          </div>
          <span className="text-sm text-defi-text-dim">Agent is thinking...</span>
        </div>
      </div>
    </div>
  )
}


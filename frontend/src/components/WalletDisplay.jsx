import React, { useState } from 'react'
import { useWalletStore } from '../stores/walletStore'

export default function WalletDisplay() {
  const { wallet, isLoading } = useWalletStore()
  const [copied, setCopied] = useState(false)
  
  const handleCopy = () => {
    navigator.clipboard.writeText(wallet.address)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  
  if (isLoading) {
    return (
      <div className="fixed top-4 right-4 z-50 bg-defi-bg-light/95 backdrop-blur-md border border-defi-border/30 rounded-full px-4 py-2 shadow-lg">
        <div className="flex items-center gap-2">
          <div className="flex space-x-1">
            <div className="w-1.5 h-1.5 bg-defi-purple rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-1.5 h-1.5 bg-defi-purple-light rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-1.5 h-1.5 bg-defi-lavender rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
          <span className="text-xs text-defi-text-dim">Loading...</span>
        </div>
      </div>
    )
  }
  
  if (!wallet) {
    return (
      <div className="fixed top-4 right-4 z-50 bg-defi-bg-light/95 backdrop-blur-md border border-defi-border/30 rounded-full px-4 py-2 shadow-lg hover:border-defi-purple/30 transition-all duration-200">
        <p className="text-xs text-defi-text-dim">No wallet</p>
      </div>
    )
  }
  
  const shortAddress = `${wallet.address.slice(0, 6)}...${wallet.address.slice(-4)}`
  
  return (
    <div className="fixed top-4 right-4 z-50 group">
      <div className="bg-defi-bg-light/95 backdrop-blur-md border border-defi-border/30 rounded-full px-4 py-2 shadow-lg hover:border-defi-purple/50 hover:shadow-glow-sm transition-all duration-200 cursor-pointer"
           onClick={handleCopy}>
        <div className="flex items-center gap-2.5">
          <span className="w-2 h-2 bg-defi-success rounded-full animate-pulse"></span>
          <span className="text-xs font-mono text-defi-text font-medium">{shortAddress}</span>
          <div className="relative">
            {copied ? (
              <svg className="w-3.5 h-3.5 text-defi-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5 text-defi-lavender group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            )}
          </div>
        </div>
      </div>
      
      {/* Tooltip */}
      <div className="absolute top-full right-0 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
        <div className="bg-defi-bg-light/95 backdrop-blur-md border border-defi-border/30 rounded-lg px-3 py-2 shadow-lg whitespace-nowrap">
          <p className="text-xs text-defi-text-dim">{copied ? 'Copied!' : 'Click to copy'}</p>
          <p className="text-xs text-defi-lavender mt-1">{wallet.network}</p>
        </div>
      </div>
    </div>
  )
}


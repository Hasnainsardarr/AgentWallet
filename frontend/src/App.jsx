import React, { useEffect, useRef } from 'react'
import { useChatStore } from './stores/chatStore'
import { useWalletStore } from './stores/walletStore'
import { getSessionId } from './utils/session'
import { sendMessage, getWallet } from './utils/api'
import WalletDisplay from './components/WalletDisplay'
import ChatMessage from './components/ChatMessage'
import ChatInput from './components/ChatInput'
import LoadingIndicator from './components/LoadingIndicator'

export default function App() {
  const sessionId = getSessionId()
  const { messages, isLoading, addMessage, setLoading } = useChatStore()
  const { wallet, setWallet, setLoading: setWalletLoading } = useWalletStore()
  const messagesEndRef = useRef(null)
  
  useEffect(() => {
    const fetchWallet = async () => {
      setWalletLoading(true)
      try {
        const data = await getWallet(sessionId)
        if (data.wallet) {
          setWallet(data.wallet)
        }
      } catch (error) {
        console.error('Failed to fetch wallet:', error)
      } finally {
        setWalletLoading(false)
      }
    }
    
    fetchWallet()
  }, [sessionId, setWallet, setWalletLoading])
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])
  
  const handleSend = async (message) => {
    addMessage({ role: 'user', content: message })
    setLoading(true)
    
    try {
      const response = await sendMessage(sessionId, message)
      
      addMessage({ role: 'assistant', content: response.response })
      
      if (response.wallet && (!wallet || wallet.address !== response.wallet.address)) {
        setWallet(response.wallet)
      }
    } catch (error) {
      console.error('Send message error:', error)
      addMessage({
        role: 'assistant',
        content: '❌ Error: Failed to process your message. Please try again.'
      })
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="flex flex-col h-screen bg-defi-bg">
      {/* Wallet Badge - Fixed Position */}
      <WalletDisplay />
      
      {/* Minimal Header */}
      <header className="border-b border-defi-border/20 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <img 
            src="https://www.infinitetrading.io/_next/image?url=%2Ftrading.png&w=640&q=75" 
            alt="ITP Wallet" 
            className="w-8 h-8 rounded-lg"
          />
          <div>
            <h1 className="text-sm font-semibold text-defi-text">ITP Wallet Agent</h1>
            <p className="text-xs text-defi-text-dim flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full"></span>
              Base Sepolia
            </p>
          </div>
        </div>
      </header>
      
      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6">
          {messages.length === 0 && (
            <div className="text-center mt-20 px-4">
              <div className="mb-8 inline-block">
                <div className="p-3 bg-defi-purple/10 rounded-2xl">
                  <svg className="w-10 h-10 text-defi-lavender" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" />
                  </svg>
                </div>
              </div>
              
              <h2 className="text-2xl font-semibold mb-3 text-defi-text">
                How can I help you today?
              </h2>
              <p className="text-sm text-defi-text-dim mb-10">
                Manage your crypto wallet with ease
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl mx-auto">
                <button className="bg-defi-bg-light/50 hover:bg-defi-bg-light border border-defi-border/30 hover:border-defi-purple/30 rounded-xl p-4 text-left transition-all duration-200 group">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-defi-purple/10 rounded-lg shrink-0">
                      <svg className="w-4 h-4 text-defi-lavender" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-defi-text mb-1">Create Wallet</p>
                      <p className="text-xs text-defi-text-dim">Set up a new wallet to get started</p>
                    </div>
                  </div>
                </button>
                
                <button className="bg-defi-bg-light/50 hover:bg-defi-bg-light border border-defi-border/30 hover:border-defi-purple/30 rounded-xl p-4 text-left transition-all duration-200 group">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-defi-success/10 rounded-lg shrink-0">
                      <svg className="w-4 h-4 text-defi-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-defi-text mb-1">Fund Wallet</p>
                      <p className="text-xs text-defi-text-dim">Add testnet ETH to your wallet</p>
                    </div>
                  </div>
                </button>
                
                <button className="bg-defi-bg-light/50 hover:bg-defi-bg-light border border-defi-border/30 hover:border-defi-purple/30 rounded-xl p-4 text-left transition-all duration-200 group">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-defi-lavender/10 rounded-lg shrink-0">
                      <svg className="w-4 h-4 text-defi-lavender" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-defi-text mb-1">Check Balance</p>
                      <p className="text-xs text-defi-text-dim">View your current balances</p>
                    </div>
                  </div>
                </button>
                
                <button className="bg-defi-bg-light/50 hover:bg-defi-bg-light border border-defi-border/30 hover:border-defi-purple/30 rounded-xl p-4 text-left transition-all duration-200 group">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-defi-warning/10 rounded-lg shrink-0">
                      <svg className="w-4 h-4 text-defi-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-defi-text mb-1">Transfer Tokens</p>
                      <p className="text-xs text-defi-text-dim">Send crypto to another address</p>
                    </div>
                  </div>
                </button>
              </div>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <ChatMessage key={idx} message={msg} />
          ))}
          
          {isLoading && <LoadingIndicator />}
          
          <div ref={messagesEndRef} />
        </div>
      </div>
      
      {/* Input Area */}
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  )
}


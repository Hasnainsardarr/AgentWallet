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
  const { wallet, setWallet } = useWalletStore()
  const messagesEndRef = useRef(null)
  
  useEffect(() => {
    const fetchWallet = async () => {
      try {
        const data = await getWallet(sessionId)
        if (data.wallet) {
          setWallet(data.wallet)
        }
      } catch (error) {
        console.error('Failed to fetch wallet:', error)
      }
    }
    
    fetchWallet()
  }, [sessionId, setWallet])
  
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
      {/* Header */}
      <header className="bg-defi-bg-light border-b border-defi-border px-6 py-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-6">
            {/* Logo */}
            <img 
              // src="/assets/logo.svg"
              src="https://www.infinitetrading.io/_next/image?url=%2Ftrading.png&w=640&q=75" 
              alt="CDP Wallet Logo" 
              className="w-16 h-16"
            />
            <div>
              <h1 className="text-2xl font-bold text-defi-text">ITP Wallet Agent</h1>
              <p className="text-sm text-defi-text-dim mt-1">Base Sepolia Testnet</p>
            </div>
          </div>
          <div className="w-72">
            <WalletDisplay />
          </div>
        </div>
      </header>
      
      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {messages.length === 0 && (
            <div className="text-center text-defi-text-dim mt-16">
              <h2 className="text-xl font-semibold mb-2 text-defi-text">Welcome to ITP Wallet Agent</h2>
              <p className="text-sm">Start by creating a wallet or asking a question</p>
              <div className="mt-8 grid grid-cols-2 gap-4 max-w-2xl mx-auto">
                <div className="bg-defi-bg-light border border-defi-border rounded-lg p-4 text-left hover:bg-defi-bg-lighter transition-colors">
                  <p className="font-medium text-defi-text mb-2">Create Wallet</p>
                  <p className="text-xs text-defi-text-dim">"Create a new wallet"</p>
                </div>
                <div className="bg-defi-bg-light border border-defi-border rounded-lg p-4 text-left hover:bg-defi-bg-lighter transition-colors">
                  <p className="font-medium text-defi-text mb-2">Fund Wallet</p>
                  <p className="text-xs text-defi-text-dim">"Fund my wallet with ETH"</p>
                </div>
                <div className="bg-defi-bg-light border border-defi-border rounded-lg p-4 text-left hover:bg-defi-bg-lighter transition-colors">
                  <p className="font-medium text-defi-text mb-2">Check Balance</p>
                  <p className="text-xs text-defi-text-dim">"Check my balance"</p>
                </div>
                <div className="bg-defi-bg-light border border-defi-border rounded-lg p-4 text-left hover:bg-defi-bg-lighter transition-colors">
                  <p className="font-medium text-defi-text mb-2">Transfer</p>
                  <p className="text-xs text-defi-text-dim">"Send 0.5 USDC to 0x..."</p>
                </div>
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


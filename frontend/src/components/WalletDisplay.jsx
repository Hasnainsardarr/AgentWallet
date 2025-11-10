import React from 'react'
import { useWalletStore } from '../stores/walletStore'

export default function WalletDisplay() {
  const { wallet } = useWalletStore()
  
  if (!wallet) {
    return (
      <div className="bg-defi-bg-light border border-defi-border rounded-lg p-4 text-center">
        <p className="text-sm text-defi-text-dim">No active wallet</p>
        <p className="text-xs mt-1 text-defi-text-dim/70">Create a wallet to get started</p>
      </div>
    )
  }
  
  const shortAddress = `${wallet.address.slice(0, 8)}...${wallet.address.slice(-6)}`
  
  return (
    <div className="bg-defi-bg-light border border-defi-border rounded-lg p-4 hover:bg-defi-bg-lighter transition-colors">
      <p className="text-xs font-semibold uppercase tracking-wider text-defi-lavender">
        Active Wallet
      </p>
      <p className="text-lg font-mono mt-2 text-defi-text">{shortAddress}</p>
      <p className="text-xs mt-2 text-defi-text-dim">{wallet.network}</p>
      <button
        onClick={() => navigator.clipboard.writeText(wallet.address)}
        className="mt-3 text-xs border border-defi-lavender text-defi-lavender hover:bg-defi-lavender/10 px-3 py-1.5 rounded-md transition-colors"
      >
        Copy Full Address
      </button>
    </div>
  )
}


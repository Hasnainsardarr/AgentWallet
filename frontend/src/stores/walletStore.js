import { create } from 'zustand'

export const useWalletStore = create((set) => ({
  wallet: null,
  
  setWallet: (wallet) => set({ wallet }),
  
  clearWallet: () => set({ wallet: null }),
}))


import { create } from 'zustand'

export const useWalletStore = create((set) => ({
  wallet: null,
  isLoading: false,
  
  setWallet: (wallet) => set({ wallet, isLoading: false }),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  clearWallet: () => set({ wallet: null, isLoading: false }),
}))


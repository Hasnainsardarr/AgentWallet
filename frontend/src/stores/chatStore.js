import { create } from 'zustand'

export const useChatStore = create((set) => ({
  messages: [],
  isLoading: false,
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  clearMessages: () => set({ messages: [] }),
}))


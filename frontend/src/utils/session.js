const SESSION_KEY = 'wallet_agent_session_id'

export const getSessionId = () => {
  let sessionId = localStorage.getItem(SESSION_KEY)
  
  if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem(SESSION_KEY, sessionId)
  }
  
  return sessionId
}

export const clearSession = () => {
  localStorage.removeItem(SESSION_KEY)
}


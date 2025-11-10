import axios from 'axios'

const api = axios.create({
  baseURL: 'https://seal-app-93xsi.ondigitalocean.app/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const sendMessage = async (sessionId, message) => {
  const response = await api.post('/chat', {
    session_id: sessionId,
    message,
  })
  console.log(response.data)
  return response.data
}

export const getWallet = async (sessionId) => {
  const response = await api.get(`/wallet/${sessionId}`)
  return response.data
}

export default api


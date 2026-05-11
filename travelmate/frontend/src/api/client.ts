import axios from 'axios'
import { getDeviceId } from '@/utils/device'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  config.headers['X-Device-ID'] = getDeviceId()
  return config
})

export default api

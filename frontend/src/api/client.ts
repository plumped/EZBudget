import axios from 'axios'

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[1]) : null
}

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

const UNSAFE_METHODS = new Set(['post', 'put', 'patch', 'delete'])

api.interceptors.request.use((config) => {
  const method = (config.method ?? 'get').toLowerCase()
  if (UNSAFE_METHODS.has(method)) {
    const token = getCookie('csrftoken')
    if (token) {
      config.headers.set('X-CSRFToken', token)
    }
  }
  return config
})

export default api

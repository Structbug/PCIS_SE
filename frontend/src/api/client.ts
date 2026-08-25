import axios from 'axios'

const client = axios.create({
  baseURL: `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1`,
  withCredentials: true,
  // Echo the double-submit CSRF cookie as a header on state-changing requests
  // (defense-in-depth on top of the backend Origin check) (H-06).
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        await axios.post(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/users/refresh`, {}, { withCredentials: true })
        return client(original)
      } catch {
        return Promise.reject(err)
      }
    }
    return Promise.reject(err)
  },
)

export default client

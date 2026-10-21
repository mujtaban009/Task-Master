import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';
export const BACKEND_API_KEY =
  import.meta.env.VITE_BACKEND_API_KEY || 'bk_live_4d9f8a2e1c7b05e3a6f82c1b9d4e7a2c';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': BACKEND_API_KEY,
  },
});

// Request Interceptor: Attach Backend API Key and JWT Bearer Access Token
apiClient.interceptors.request.use(
  (config) => {
    config.headers['X-API-Key'] = BACKEND_API_KEY;
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

let refreshInFlight: Promise<string> | null = null;

// Response Interceptor: Handle Token Expiration & Refresh Flow
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');

      if (refreshToken) {
        try {
          // Requests that fail together share one refresh: a second call with the
          // same single-use token would look like theft and end every session
          refreshInFlight ??= axios
            .post(
              `${API_BASE_URL}/auth/refresh`,
              { refresh_token: refreshToken },
              {
                headers: {
                  'Content-Type': 'application/json',
                  'X-API-Key': BACKEND_API_KEY,
                },
              }
            )
            .then((res) => {
              const { access_token, refresh_token } = res.data;
              localStorage.setItem('access_token', access_token);
              localStorage.setItem('refresh_token', refresh_token);
              return access_token as string;
            })
            .finally(() => {
              refreshInFlight = null;
            });

          const accessToken = await refreshInFlight;
          originalRequest.headers.Authorization = `Bearer ${accessToken}`;
          return apiClient(originalRequest);
        } catch (refreshErr) {
          // Token refresh failed -> Clear session and redirect to login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);


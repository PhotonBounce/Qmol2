import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/store/auth';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach API key
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const key = useAuthStore.getState().apiKey;
    if (key && config.headers) {
      config.headers['x-api-key'] = key;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle errors
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: number };
    
    if (!originalRequest) return Promise.reject(error);

    // 429 Too Many Requests - retry with exponential backoff
    if (error.response?.status === 429) {
      const retryCount = originalRequest._retry || 0;
      if (retryCount < 3) {
        originalRequest._retry = retryCount + 1;
        const delay = Math.pow(2, retryCount) * 1000;
        await new Promise((resolve) => setTimeout(resolve, delay));
        return apiClient(originalRequest);
      }
    }

    // 401 Unauthorized - clear auth
    if (error.response?.status === 401) {
      useAuthStore.getState().clearAuth();
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }

    // 402 Payment Required / Quota exceeded
    if (error.response?.status === 402) {
      window.dispatchEvent(new CustomEvent('auth:quota_exceeded'));
    }

    return Promise.reject(error);
  }
);

export default apiClient;

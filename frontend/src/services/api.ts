import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { supabase } from './supabase';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Extend the AxiosRequestConfig to include the _retry property
declare module 'axios' {
  interface InternalAxiosRequestConfig<D = any> {
    _retry?: boolean;
  }
}

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      async (config) => {
        try {
          const { data: { session } } = await supabase.auth.getSession();
          if (session?.access_token) {
            // Create a new config with the authorization header
            const newConfig = { ...config };
            
            // Use Axios's header methods to ensure type safety
            if (newConfig.headers) {
              // If headers is a plain object, convert it to AxiosHeaders
              if (typeof newConfig.headers === 'object' && !('set' in newConfig.headers)) {
                const headers = new axios.AxiosHeaders();
                Object.entries(newConfig.headers).forEach(([key, value]) => {
                  headers.set(key, value as string);
                });
                newConfig.headers = headers;
              }
              
              // Set the Authorization header
              newConfig.headers.set('Authorization', `Bearer ${session.access_token}`);
            } else {
              // If no headers exist, create new AxiosHeaders
              newConfig.headers = new axios.AxiosHeaders({
                'Authorization': `Bearer ${session.access_token}`
              });
            }
            
            return newConfig;
          }
          return config;
        } catch (error) {
          console.error('Error in request interceptor:', error);
          return Promise.reject(error);
        }
      },
      (error) => {
        console.error('Request interceptor error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
        
        // If error is 401 and we haven't tried to refresh yet
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          try {
            // Try to refresh the session
            const { data, error: refreshError } = await supabase.auth.refreshSession();
            
            if (refreshError) throw refreshError;
            
            // Retry the original request with new token
            if (data.session?.access_token) {
              // Create a new config with the updated token
              const newConfig = {
                ...originalRequest,
                headers: {
                  ...originalRequest.headers,
                  'Authorization': `Bearer ${data.session.access_token}`
                }
              };
              
              return this.client.request(newConfig);
            }
          } catch (refreshError) {
            console.error('Session refresh failed:', refreshError);
            // If refresh fails, sign out and redirect to login
            await supabase.auth.signOut();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }
        
        // If we've already tried refreshing or it's not a 401 error
        if (error.response?.status === 401) {
          // If we get here, the refresh token might be invalid
          await supabase.auth.signOut();
          window.location.href = '/login';
        }
        
        return Promise.reject(error);
      }
    );
  }

  // File management methods
  async uploadFile(file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const { data: { session } } = await supabase.auth.getSession();
    
    const response = await this.client.post('/files/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': session?.access_token ? `Bearer ${session.access_token}` : '',
      },
    });

    return response.data;
  }

  async connectGoogleSheet(sheetUrl: string, sheetName?: string) {
    const response = await this.client.post('/files/google-sheet/', {
      sheet_url: sheetUrl,
      sheet_name: sheetName,
    });

    return response.data;
  }

  async getFiles() {
    const response = await this.client.get('/files/list/');
    return response.data;
  }

  async getFilePreview(fileId: number) {
    const response = await this.client.get(`/files/preview/${fileId}/`);
    return response.data;
  }

  async deleteFile(fileId: number) {
    const response = await this.client.delete(`/files/delete/${fileId}/`);
    return response.data;
  }

  // Chat methods
  async sendChatMessage(message: string, fileId: number, sessionId?: string) {
    const response = await this.client.post('/ai/chat/', {
      message,
      file_id: fileId,
      session_id: sessionId,
    });

    return response.data;
  }

  // Dashboard methods
  async generateDashboard(fileId: number, query?: string, theme?: any) {
    const response = await this.client.post('/ai/dashboard/', {
      file_id: fileId,
      query,
      theme,
    });

    return response.data;
  }

  async getDashboard(dashboardId: number) {
    const response = await this.client.get(`/ai/dashboard/${dashboardId}/`);
    return response.data;
  }

  async exportDashboard(dashboardId: number, format: string = 'pdf') {
    const response = await this.client.post(`/ai/dashboard/${dashboardId}/export/`, {
      format,
    });

    return response.data;
  }

  // New dashboard saving methods
  async saveDashboardToSupabase(dashboardId: number) {
    const response = await this.client.post(`/ai/dashboard/${dashboardId}/save/`);
    return response.data;
  }

  async listUserDashboards() {
    const response = await this.client.get(`/ai/dashboards/list/`);
    return response.data;
  }

  async loadUserDashboard(filename: string) {
    const response = await this.client.get(`/ai/dashboards/load/${filename}/`);
    return response.data;
  }

  // Theme/Color methods
  async getColorGrid() {
    // This would be a separate endpoint for color selection
    // For now, return static color options
    return {
      color_grid: [
        {
          base: '#1f77b4',
          variations: ['#1f77b4', '#6baed6', '#084d7a']
        },
        {
          base: '#ff7f0e',
          variations: ['#ff7f0e', '#ffbb78', '#b8550c']
        },
        {
          base: '#2ca02c',
          variations: ['#2ca02c', '#98df8a', '#1e6b1e']
        }
      ],
      presets: [
        {
          name: 'Default Blue',
          text: '#333333',
          chart: '#1f77b4',
          background: '#ffffff'
        },
        {
          name: 'Dark Mode',
          text: '#ffffff',
          chart: '#60a5fa',
          background: '#1f2937'
        }
      ]
    };
  }

  async previewTheme(textColor: string, chartColor: string, backgroundColor: string) {
    return {
      theme: {
        colors: {
          text: textColor,
          chart: chartColor,
          background: backgroundColor,
          primary: chartColor,
        }
      },
      contrast_ratio: 4.5, // This would be calculated
      accessibility: 'AA'
    };
  }

  // Utility methods
  setAuthToken(token: string) {
    localStorage.setItem('auth_token', token);
  }

  getAuthToken() {
    return localStorage.getItem('auth_token');
  }

  removeAuthToken() {
    localStorage.removeItem('auth_token');
  }

  isAuthenticated() {
    return !!this.getAuthToken();
  }
}

// Create and export singleton instance
const apiService = new ApiService();
export default apiService;

import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add JWT token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (email, password) => api.post('/auth/register', { email, password }),
  login: (email, password) => api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
};

export const profileAPI = {
  get: () => api.get('/profile'),
  update: (data) => api.put('/profile', data),
};

export const applicationsAPI = {
  list: () => api.get('/applications'),
  get: (id) => api.get(`/applications/${id}`),
  create: (scholarshipId) => api.post('/applications', { scholarship_id: scholarshipId }),
  update: (id, data) => api.put(`/applications/${id}`, data),
  delete: (id) => api.delete(`/applications/${id}`),
  updateChecklistItem: (appId, itemId, data) =>
    api.put(`/applications/${appId}/checklist/${itemId}`, data),
};

export const essaysAPI = {
  list: (params) => api.get('/essays', { params }),
  get: (id) => api.get(`/essays/${id}`),
  create: (data) => api.post('/essays', data),
  update: (id, data) => api.put(`/essays/${id}`, data),
  delete: (id) => api.delete(`/essays/${id}`),
};

export const documentsAPI = {
  list: (params) => api.get('/documents', { params }),
  get: (id) => api.get(`/documents/${id}`),
  upload: (file, metadata) => {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      Object.entries(metadata).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          formData.append(key, value);
        }
      });
    }
    return api.post('/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  download: (id) => api.get(`/documents/${id}/download`, { responseType: 'blob' }),
  update: (id, data) => api.put(`/documents/${id}`, data),
  delete: (id) => api.delete(`/documents/${id}`),
};

export const scholarshipsAPI = {
  list: (params) => api.get('/scholarships', { params }),
  get: (id) => api.get(`/scholarships/${id}`),
};

export const llmAPI = {
  status: () => api.get('/llm/status'),
  getMatchExplanation: (scholarshipId) => api.get(`/llm/match-explanation/${scholarshipId}`),
  parseScholarship: (rawText, name) => api.post('/llm/parse-scholarship', { raw_text: rawText, name }),
};

export const agentAPI = {
  // Agent status
  status: () => api.get('/agent/status'),

  // Chat with agent
  chat: (message, sessionId = null) => api.post('/agent/chat', {
    message,
    session_id: sessionId,
  }),

  // Session management
  listSessions: (limit = 10) => api.get('/agent/sessions', { params: { limit } }),
  getSession: (sessionId) => api.get(`/agent/sessions/${sessionId}`),
  archiveSession: (sessionId) => api.delete(`/agent/sessions/${sessionId}`),

  // Recommendations
  getRecommendations: (limit = 5, excludeApplied = true) =>
    api.get('/agent/recommendations', { params: { limit, exclude_applied: excludeApplied } }),

  // Quick actions
  quickSearch: (params) => api.post('/agent/quick/search', params),
  quickMatch: (scholarshipId) => api.get(`/agent/quick/match/${scholarshipId}`),
  quickChecklist: (applicationId) => api.get(`/agent/quick/checklist/${applicationId}`),
};

export const scraperAPI = {
  // Status and stats
  status: () => api.get('/scraper/status'),
  sources: () => api.get('/scraper/sources'),

  // Job management
  startJob: (source, mode = 'incremental') => api.post('/scraper/jobs', { source, mode }),
  listJobs: (params = {}) => api.get('/scraper/jobs', { params }),
  getJob: (jobId) => api.get(`/scraper/jobs/${jobId}`),
  cancelJob: (jobId) => api.delete(`/scraper/jobs/${jobId}`),

  // Logs
  getLogs: (params = {}) => api.get('/scraper/logs', { params }),

  // Configuration
  listConfigs: () => api.get('/scraper/config'),
  getConfig: (source) => api.get(`/scraper/config/${source}`),
  updateConfig: (source, config) => api.put(`/scraper/config/${source}`, config),
};

export default api;

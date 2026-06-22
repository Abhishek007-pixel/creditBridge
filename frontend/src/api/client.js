import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
});

// Auto-attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cb_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const registerApplicant = (data) => api.post('/api/register', data);
export const login = (username, password) => api.post('/api/auth/login', { username, password });
export const saveConsent = (data) => api.post('/api/consent', data);
export const saveQuestionnaire = (applicant_id, answers) =>
  api.post('/api/questionnaire', { applicant_id, answers });
export const scoreApplicant = (applicant_id, answers) =>
  api.post('/api/score', { applicant_id, questionnaire_answers: answers });
export const getReport = (applicant_id) => api.get(`/api/report/${applicant_id}`);
export const getAllApplicants = () => api.get('/api/applicants');
export const getWeights = () => api.get('/api/admin/weights');
export const updateWeights = (weights) => api.put('/api/admin/weights', { weights });
export const getAnalytics = () => api.get('/api/admin/analytics');

export default api;

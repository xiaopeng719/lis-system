import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
});

// 请求拦截器 — 自动带上 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('lis_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器 — 401 自动跳登录
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('lis_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;

// ==================== Auth ====================
export const authApi = {
  login: (data: { username: string; password: string }) =>
    api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
  permissions: () => api.get('/auth/permissions'),
  listUsers: () => api.get('/auth/users'),
  createUser: (data: any) => api.post('/auth/users', data),
  updateUser: (id: number, data: any) => api.put(`/auth/users/${id}`, data),
};

// ==================== Dashboard ====================
export const dashboardApi = {
  stats: () => api.get('/dashboard/stats'),
  tat: () => api.get('/dashboard/tat'),
  instruments: () => api.get('/instrument-status/status'),
  notifications: () => api.get('/dashboard/notifications'),
};

// ==================== Patients ====================
export const patientApi = {
  list: (params?: any) => api.get('/patients', { params }),
  create: (data: any) => api.post('/patients', data),
  get: (id: number) => api.get(`/patients/${id}`),
};

// ==================== Specimens ====================
export const specimenApi = {
  list: (params?: any) => api.get('/specimens', { params }),
  create: (data: any) => api.post('/specimens', data),
  receive: (id: number, data: any) => api.post(`/specimens/${id}/receive`, data),
  complete: (id: number) => api.post(`/specimens/${id}/complete`),
  enterResults: (id: number, data: any[]) => api.post(`/specimens/${id}/enter-results`, data),
  getTestItems: (id: number) => api.get(`/specimens/${id}/test-items`),
  reject: (id: number, data: any) => api.post(`/specimens/${id}/reject`, data),
};

// ==================== Orders ====================
export const orderApi = {
  list: (params?: any) => api.get('/orders', { params }),
  create: (data: any) => api.post('/orders', data),
  cancel: (id: number) => api.post(`/orders/${id}/cancel`),
};

// ==================== Results ====================
export const resultApi = {
  list: (params?: any) => api.get('/results', { params }),
  bySpecimen: (specimenId: number) => api.get(`/results/by-specimen/${specimenId}`),
  review: (data: any) => api.post('/results/review', data),
  manual: (data: any) => api.post('/results/manual', data),
};

// ==================== Reports ====================
export const reportApi = {
  list: (params?: any) => api.get('/reports', { params }),
  generate: (specimenId: number) => api.post(`/reports/generate/${specimenId}`),
  get: (id: number) => api.get(`/reports/${id}`),
  review: (id: number, reviewer: string) =>
    api.post(`/reports/${id}/review?reviewer=${reviewer}`),
};

// ==================== Instruments ====================
export const instrumentApi = {
  list: () => api.get('/instruments'),
  create: (data: any) => api.post('/instruments', data),
  get: (id: number) => api.get(`/instruments/${id}`),
  // 通道号管理
  getChannels: (instrumentId: number) => api.get(`/instruments/${instrumentId}/channels`),
  createChannel: (instrumentId: number, data: any) => api.post(`/instruments/${instrumentId}/channels`, data),
  deleteChannel: (instrumentId: number, channelId: number) => api.delete(`/instruments/${instrumentId}/channels/${channelId}`),
};

// ==================== Base Data ====================
export const baseDataApi = {
  departments: () => api.get('/base-data/departments'),
  createDepartment: (data: any) => api.post('/base-data/departments', data),
  // 检验项目
  testItems: (category?: string) =>
    api.get('/base-data/test-items', { params: { category } }),
  createTestItem: (data: any) => api.post('/base-data/test-items', data),
  updateTestItem: (id: number, data: any) => api.put(`/base-data/test-items/${id}`, data),
  deleteTestItem: (id: number) => api.delete(`/base-data/test-items/${id}`),
  // 组合项目
  getCombos: () => api.get('/base-data/combos'),
  createCombo: (data: any) => api.post('/base-data/combos', data),
  updateCombo: (id: number, data: any) => api.put(`/base-data/combos/${id}`, data),
  deleteCombo: (id: number) => api.delete(`/base-data/combos/${id}`),
  initAdmin: () => api.post('/base-data/init-admin'),
};

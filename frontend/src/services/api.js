/**
 * API Service Layer — Centralized API calls to the GenAI Platform backend.
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

const api = axios.create({
    baseURL: API_BASE,
    headers: { 'Content-Type': 'application/json' },
});

// ─── Projects ───

export const createProject = (name, description = '') =>
    api.post('/projects', { name, description }).then(r => r.data);

export const getProjects = () =>
    api.get('/projects').then(r => r.data);

export const getProject = (projectId) =>
    api.get(`/projects/${projectId}`).then(r => r.data);

export const deleteProject = (projectId) =>
    api.delete(`/projects/${projectId}`).then(r => r.data);


export const exportProject = async (projectId) => {
    const res = await api.get(`/projects/${projectId}/export`, { responseType: 'blob' });
    const blob = new Blob([res.data], { type: 'application/zip' });
    const url = URL.createObjectURL(blob);
    // Extract filename from Content-Disposition header, fallback to generic
    const disposition = res.headers['content-disposition'] || '';
    const match = disposition.match(/filename="?(.+?)"?$/);
    const filename = match ? match[1] : 'project_export.zip';
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
};

export const importProject = (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/projects/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
};

// ─── Agent Config ───

export const getAgentConfig = (projectId) =>
    api.get(`/projects/${projectId}/config`).then(r => r.data);

export const updateAgentConfig = (projectId, updates) =>
    api.put(`/projects/${projectId}/config`, updates).then(r => r.data);

// ─── Documents ───

export const uploadDocument = (projectId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/projects/${projectId}/documents/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
};

export const getDocuments = (projectId) =>
    api.get(`/projects/${projectId}/documents`).then(r => r.data);

export const deleteDocument = (projectId, documentId) =>
    api.delete(`/projects/${projectId}/documents/${documentId}`).then(r => r.data);

// ─── Transactions ───

export const getTransactions = (projectId) =>
    api.get(`/projects/${projectId}/transactions`).then(r => r.data);

export const seedTransactions = (projectId) =>
    api.post(`/projects/${projectId}/transactions/seed`).then(r => r.data);

export const importCSV = (projectId, file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post(`/projects/${projectId}/transactions/import-csv`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
};

export const testExternalConnection = (projectId, connectionString, tableName) =>
    api.post(`/projects/${projectId}/transactions/test-connection`, {
        connection_string: connectionString,
        table_name: tableName,
    }).then(r => r.data);

// ─── Chat ───

export const sendMessage = (projectId, message, history = [], sessionId = 'default') =>
    api.post(`/projects/${projectId}/chat`, { message, session_id: sessionId, history }).then(r => r.data);

// ─── Logs ───

export const getQueryLogs = (projectId, limit = 50) =>
    api.get(`/projects/${projectId}/logs`, { params: { limit } }).then(r => r.data);

// ─── Health ───

export const healthCheck = () =>
    api.get('/health').then(r => r.data);

export default api;

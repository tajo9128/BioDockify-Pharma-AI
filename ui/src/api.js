import axios from 'axios';

// Configure Axios
const api = axios.create({
    baseURL: '',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response.data,
    (error) => {
        console.error('API Error:', error.response || error.message);
        return Promise.reject(error);
    }
);

export const apiService = {
    // Start a new research task
    startResearch: async (title, mode = 'local') => {
        return api.post('/api/research/start', { title, mode });
    },

    // Get status of a specific task
    getTaskStatus: async (taskId) => {
        return api.get(`/api/research/status/${taskId}`);
    },

    // Get knowledge graph statistics
    getGraphStats: async () => {
        return api.get('/api/graph/stats');
    },

    // Health check
    healthCheck: async () => {
        return api.get('/api/health');
    },

    // Enhanced Project System (Phase 11)
    getEnhancedProjects: async () => {
        return api.get('/api/enhanced/projects');
    },

    getEnhancedProjectStatus: async (projectId) => {
        return api.get(`/api/enhanced/project/${projectId}`);
    },

    getEnhancedSystemStatus: async () => {
        return api.get('/api/enhanced/system/status');
    },

    createEnhancedProject: async (title, type, context = '') => {
        return api.post(`/api/enhanced/project?project_title=${encodeURIComponent(title)}&project_type=${encodeURIComponent(type)}&additional_context=${encodeURIComponent(context)}`);
    },

    // Export statistics analysis result
    exportStatistics: async (result, format, includeAssumptions = true, includeInterpretation = true, includeCode = false) => {
        return api.post('/api/statistics/export', {
            analysis_id: result.analysis_id,
            format: format,
            include_assumptions: includeAssumptions,
            include_interpretation: includeInterpretation,
            include_code: includeCode
        });
    }
};

export default apiService;

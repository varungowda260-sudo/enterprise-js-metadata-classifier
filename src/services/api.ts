// API Service for JavaScript Metadata Classification Backend

import type {
  ProcessingStats,
  ClassificationResult,
  MetadataRecord,
  LogEntry,
  FilterRule,
  UploadResponse,
  ProcessResponse,
  SearchQuery,
  ParserTestResult,
} from '@/types';

// Use empty string for relative URLs (works with Vite proxy)
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  'https://enterprise-js-metadata-api.onrender.com';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'DELETE';
  body?: unknown;
}

async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body } = options;

  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (body && method !== 'GET') {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Health check
  health: () => apiRequest<{ status: string; service: string; version: string }>('/'),

  // Upload and process
  uploadZip: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  processZip: async (file: File): Promise<ProcessResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/process-zip`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Processing failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  processFolder: (folderPath: string) =>
    apiRequest<ProcessResponse>('/api/process-folder', {
      method: 'POST',
      body: { folder_path: folderPath },
    }),

  // Control processing
  pause: () => apiRequest<{ status: string }>('/api/pause', { method: 'POST' }),
  resume: () => apiRequest<{ status: string }>('/api/resume', { method: 'POST' }),
  cancel: () => apiRequest<{ status: string }>('/api/cancel', { method: 'POST' }),
  reset: () => apiRequest<{ status: string }>('/api/reset', { method: 'POST' }),

  // Get data
  getStats: () => apiRequest<ProcessingStats>('/api/stats'),
  getClassifications: () =>
    apiRequest<{ classifications: ClassificationResult[] }>('/api/classifications'),
  getRecords: () =>
    apiRequest<{ records: MetadataRecord[] }>('/api/records'),

  search: (query: SearchQuery) =>
    apiRequest<{ results: ClassificationResult[] }>('/api/search', {
      method: 'POST',
      body: query,
    }),

  // Logs
  getLogs: () =>
    apiRequest<{ entries: LogEntry[]; summary: Record<string, unknown> }>('/api/logs'),

  exportLogs: (format: 'json' | 'csv') =>
    `${API_BASE_URL}/api/logs/export?format=${format}`,

  // Export
  exportExcel: () => `${API_BASE_URL}/api/export/excel`,

  // Filters
  getFilters: () =>
    apiRequest<{ filters: Array<{ type: string; description: string }> }>('/api/filters'),

  addFilter: (rule: FilterRule) =>
    apiRequest<{ status: string; rule: FilterRule }>('/api/filters/add', {
      method: 'POST',
      body: rule,
    }),

  resetFilters: () =>
    apiRequest<{ status: string }>('/api/filters/reset', { method: 'DELETE' }),

  // Parser Test
  testParser: async (file: File): Promise<ParserTestResult> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/parser-test`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Parser test failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },
};

// WebSocket connection
export function createWebSocket(onMessage: (data: unknown) => void): WebSocket {
  // Determine WebSocket URL based on current location
  // Create WebSocket URL from backend API URL
const apiUrl =
  import.meta.env.VITE_API_URL ||
  'https://enterprise-js-metadata-api.onrender.com';

const wsUrl = apiUrl
  .replace('https://', 'wss://')
  .replace('http://', 'ws://')
  + '/ws';

console.log('[WS] Creating WebSocket URL:', wsUrl);

  const ws = new WebSocket(wsUrl);
  console.log(
    '[WS] WebSocket instance created, readyState:', 
     ws.readyState, 
     '(0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED)'
  );

  ws.onopen = () => {
    console.log('[WS] onopen event fired - Connection established');
    console.log('[WS] readyState after open:', ws.readyState);
  };

  ws.onmessage = (event) => {
    console.log('[WS] onmessage event fired, data:', event.data.substring(0, 100) + '...');
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('[WS] Failed to parse WebSocket message:', e);
    }
  };

  ws.onerror = (error) => {
    console.error('[WS] onerror event fired:', error);
    console.error('[WS] readyState on error:', ws.readyState);
  };

  ws.onclose = (event) => {
    console.log('[WS] onclose event fired');
    console.log('[WS] Close code:', event.code, 'reason:', event.reason, 'clean:', event.wasClean);
    console.log('[WS] readyState after close:', ws.readyState);
  };

  return ws;
}

// Custom hooks for JavaScript Metadata Classification

import { useState, useEffect, useCallback, useRef } from 'react';
import { api, createWebSocket } from '@/services/api';
import type {
  ProcessingStats,
  ClassificationResult,
  LogEntry,
  FilterRule,
} from '@/types';

const initialStats: ProcessingStats = {
  total_files_found: 0,
  files_processed: 0,
  files_remaining: 0,
  valid_records: 0,
  cancelled_records: 0,
  files_with_errors: 0,
  unique_systems: 0,
  elapsed_seconds: 0,
  estimated_remaining_seconds: 0,
  files_per_second: 0,
  status: 'pending',
  current_file: '',
  current_system: '',
  current_status: '',
};

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const [lastMessage, setLastMessage] = useState<unknown>(null);

  useEffect(() => {
    wsRef.current = createWebSocket((data) => {
      setLastMessage(data);
      setIsConnected(true);
    });

    wsRef.current.onopen = () => setIsConnected(true);
    wsRef.current.onclose = () => setIsConnected(false);

    return () => {
      wsRef.current?.close();
    };
  }, []);

  const sendMessage = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { isConnected, lastMessage, sendMessage };
}

export function useProcessingStats() {
  const [stats, setStats] = useState<ProcessingStats>(initialStats);

  const fetchStats = useCallback(async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  }, []);

  return { stats, setStats, fetchStats };
}

export function useClassifications() {
  const [classifications, setClassifications] = useState<ClassificationResult[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchClassifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getClassifications();
      setClassifications(data.classifications);
    } catch (error) {
      console.error('Failed to fetch classifications:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  return { classifications, loading, fetchClassifications };
}

export function useLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getLogs();
      setLogs(data.entries);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  return { logs, loading, fetchLogs };
}

export function useFilters() {
  const [filters, setFilters] = useState<FilterRule[]>([]);

  const addFilter = useCallback(async (rule: FilterRule) => {
    try {
      await api.addFilter(rule);
    } catch (error) {
      console.error('Failed to add filter:', error);
      throw error;
    }
  }, []);

  const resetFilters = useCallback(async () => {
    try {
      await api.resetFilters();
      setFilters([]);
    } catch (error) {
      console.error('Failed to reset filters:', error);
      throw error;
    }
  }, []);

  return { filters, addFilter, resetFilters };
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (minutes < 60) {
    return `${minutes}m ${secs}s`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

export function formatNumber(num: number): string {
  return num.toLocaleString();
}

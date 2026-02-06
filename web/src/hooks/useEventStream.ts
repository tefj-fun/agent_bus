import { useEffect, useState, useCallback, useRef } from 'react';
import { createEventSource } from '../api/client';
import type { AgentEvent } from '../types';

interface UseEventStreamOptions {
  jobId?: string;
  onEvent?: (event: AgentEvent) => void;
  maxEvents?: number;
}

export function useEventStream({ jobId, onEvent, maxEvents = 10 }: UseEventStreamOptions = {}) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttempts = useRef(0);
  const historyLoadedRef = useRef(false);

  useEffect(() => {
    if (!jobId || historyLoadedRef.current) return;

    const controller = new AbortController();
    fetch(`/api/events/history?job_id=${jobId}&limit=${maxEvents}`, {
      signal: controller.signal,
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((payload) => {
        if (payload?.events && Array.isArray(payload.events)) {
          setEvents((payload.events as AgentEvent[]).slice(0, maxEvents));
          historyLoadedRef.current = true;
        }
      })
      .catch(() => undefined);

    return () => controller.abort();
  }, [jobId, maxEvents]);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = createEventSource(jobId);
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setError(null);
      reconnectAttempts.current = 0;
    };

    es.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);
        // Transform to AgentEvent format with unique id
        const rawType = raw.type || 'info';
        const errorText = raw.data?.error || raw.data?.reason;
        const fallbackMessage = raw.data?.message || `${rawType}: ${raw.data?.stage || raw.data?.job_id || ''}`;
        const message = (rawType === 'job_failed' || rawType === 'task_failed' || rawType === 'failed')
          ? (errorText ? `Failed: ${errorText}` : fallbackMessage)
          : fallbackMessage;

        const data: AgentEvent = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          type: rawType,
          message,
          timestamp: raw.timestamp || new Date().toISOString(),
          agent: raw.data?.agent,
          job_id: raw.data?.job_id,
          metadata: raw.data,
        };
        setEvents((prev) => {
          const newEvents = [data, ...prev].slice(0, maxEvents);
          return newEvents;
        });
        onEvent?.(data);
      } catch (e) {
        console.error('Failed to parse SSE event:', e);
      }
    };

    es.onerror = () => {
      setConnected(false);
      setError('Connection lost');
      es.close();

      // Reconnect with exponential backoff
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
      reconnectAttempts.current += 1;

      if (reconnectAttempts.current < 10) {
        reconnectTimeoutRef.current = window.setTimeout(connect, delay);
      } else {
        setError('Connection failed after multiple attempts');
      }
    };
  }, [jobId, onEvent, maxEvents]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  const clearEvents = useCallback(() => {
    setEvents([]);
    historyLoadedRef.current = false;
  }, []);

  return {
    events,
    connected,
    error,
    clearEvents,
    reconnect: connect,
  };
}

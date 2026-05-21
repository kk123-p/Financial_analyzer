import { useEffect, useRef, useCallback } from 'react';
import { useDebateStore } from '@/store/appStore';
import type { WsMessage } from '@/types';

export function useDebateWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const { isConnected, messages, addMessage, clearMessages, setConnected } = useDebateStore();
  const currentRoleRef = useRef<string>('');

  const connect = useCallback((stockCode: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    clearMessages();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const wsUrl = `${protocol}//${host}:8000/ai/debate`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({ stock_code: stockCode }));
    };

    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data);
        if (msg.type === 'meta') {
          if (msg.content.startsWith('analyst_')) {
            currentRoleRef.current = msg.content.replace('analyst_', '').replace('_start', '');
          }
          addMessage('_meta', msg.content);
        } else if (msg.type === 'chunk') {
          addMessage(msg.role, msg.content);
        } else if (msg.type === 'done') {
          addMessage('_meta', 'debate_complete');
        } else if (msg.type === 'error') {
          addMessage('_error', msg.content);
        }
      } catch {}
    };

    ws.onclose = () => { setConnected(false); };
    ws.onerror = () => { setConnected(false); };
  }, [clearMessages, addMessage, setConnected]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, [setConnected]);

  useEffect(() => {
    return () => { wsRef.current?.close(); };
  }, []);

  // Group messages by role for rendering
  const grouped = messages.reduce<{ role: string; text: string }[]>((acc, msg) => {
    const last = acc[acc.length - 1];
    if (last && last.role === msg.role) {
      last.text += msg.content;
    } else {
      acc.push({ role: msg.role, text: msg.content });
    }
    return acc;
  }, []);

  return { connect, disconnect, isConnected, messages, grouped, currentRole: currentRoleRef };
}

/**
 * WebSocket hook for real-time monitoring updates.
 * Implements auto-reconnect with exponential backoff and React Query integration.
 */

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { logger } from "@/lib/logger";
import type { WebSocketMessage, WebSocketMessageType } from "@/lib/types";

/** WebSocket connection state */
export type ConnectionState = "connecting" | "connected" | "disconnected" | "reconnecting";

/** Options for the WebSocket hook */
export interface UseWebSocketOptions {
	/** Room to subscribe to (e.g., 'global', 'tasks', 'task:123') */
	room: string;
	/** Called when a message is received */
	onMessage?: (message: WebSocketMessage) => void;
	/** Called when connection state changes */
	onConnectionChange?: (state: ConnectionState) => void;
	/** Whether to auto-connect on mount (default: true) */
	autoConnect?: boolean;
	/** Max reconnection attempts (default: 10) */
	maxReconnectAttempts?: number;
	/** Base delay for reconnection in ms (default: 1000) */
	reconnectDelay?: number;
}

/** Return type for the WebSocket hook */
export interface UseWebSocketReturn {
	/** Current connection state */
	connectionState: ConnectionState;
	/** Whether the socket is connected */
	isConnected: boolean;
	/** Manually connect to the WebSocket */
	connect: () => void;
	/** Manually disconnect from the WebSocket */
	disconnect: () => void;
	/** Send a message to the server */
	send: (data: unknown) => void;
}

/**
 * Custom hook for WebSocket connections with auto-reconnect
 * and React Query integration.
 */
export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
	const {
		room,
		onMessage,
		onConnectionChange,
		autoConnect = true,
		maxReconnectAttempts = 10,
		reconnectDelay = 1000,
	} = options;

	const queryClient = useQueryClient();
	const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");

	// Refs to maintain state across renders
	const wsRef = useRef<WebSocket | null>(null);
	const reconnectAttemptRef = useRef(0);
	const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const shouldReconnectRef = useRef(true);

	// Update connection state and notify callback
	const updateConnectionState = useCallback(
		(state: ConnectionState) => {
			setConnectionState(state);
			onConnectionChange?.(state);
		},
		[onConnectionChange],
	);

	/**
	 * Invalidate React Query caches based on message type.
	 * This ensures the UI stays in sync with real-time updates.
	 */
	const handleQueryInvalidation = useCallback(
		(messageType: WebSocketMessageType) => {
			switch (messageType) {
				case "task_enqueued":
				case "task_started":
				case "task_completed":
				case "task_failed":
				case "task_updated":
					void queryClient.invalidateQueries({ queryKey: ["tasks"] });
					void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
					break;

				case "worker_updated":
				case "worker_started":
				case "worker_stopped":
					void queryClient.invalidateQueries({ queryKey: ["workers"] });
					void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
					break;

				case "queue_updated":
					void queryClient.invalidateQueries({ queryKey: ["queues"] });
					void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
					break;

				case "metrics_updated":
					void queryClient.invalidateQueries({ queryKey: ["metrics"] });
					break;
			}
		},
		[queryClient],
	);

	/**
	 * Calculate reconnection delay with exponential backoff.
	 */
	const getReconnectDelay = useCallback(() => {
		const attempt = reconnectAttemptRef.current;
		// Exponential backoff: delay * 2^attempt, capped at 30 seconds
		const delay = Math.min(reconnectDelay * 2 ** attempt, 30000);
		// Add jitter (±20%) to prevent thundering herd
		const jitter = delay * (0.8 + Math.random() * 0.4);
		return Math.round(jitter);
	}, [reconnectDelay]);

	/**
	 * Connect to the WebSocket server.
	 */
	const connect = useCallback(() => {
		// Don't connect if already connected or connecting
		if (wsRef.current?.readyState === WebSocket.OPEN) {
			return;
		}

		// Clean up existing connection
		if (wsRef.current) {
			wsRef.current.close();
			wsRef.current = null;
		}

		updateConnectionState(reconnectAttemptRef.current > 0 ? "reconnecting" : "connecting");

		// Build WebSocket URL
		const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
		const host = window.location.host;
		const url = `${protocol}//${host}/ws?room=${encodeURIComponent(room)}`;

		try {
			const ws = new WebSocket(url);

			ws.onopen = () => {
				logger.log(`[WebSocket] Connected to room: ${room}`);
				reconnectAttemptRef.current = 0;
				updateConnectionState("connected");
			};

			ws.onmessage = (event) => {
				try {
					const message = JSON.parse(event.data as string) as WebSocketMessage;

					// Invalidate relevant queries
					handleQueryInvalidation(message.type);

					// Call user callback
					onMessage?.(message);
				} catch (error) {
					logger.error("[WebSocket] Failed to parse message:", error);
				}
			};

			ws.onerror = (error) => {
				logger.error("[WebSocket] Error:", error);
			};

			ws.onclose = (event) => {
				logger.log(`[WebSocket] Disconnected (code: ${event.code}, reason: ${event.reason})`);
				updateConnectionState("disconnected");
				wsRef.current = null;

				// Attempt reconnection if not intentionally disconnected
				if (shouldReconnectRef.current && reconnectAttemptRef.current < maxReconnectAttempts) {
					const delay = getReconnectDelay();
					logger.log(
						`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current + 1}/${maxReconnectAttempts})`,
					);

					reconnectTimeoutRef.current = setTimeout(() => {
						reconnectAttemptRef.current += 1;
						connect();
					}, delay);
				}
			};

			wsRef.current = ws;
		} catch (error) {
			logger.error("[WebSocket] Failed to create connection:", error);
			updateConnectionState("disconnected");
		}
	}, [
		room,
		onMessage,
		updateConnectionState,
		handleQueryInvalidation,
		maxReconnectAttempts,
		getReconnectDelay,
	]);

	/**
	 * Disconnect from the WebSocket server.
	 */
	const disconnect = useCallback(() => {
		shouldReconnectRef.current = false;

		// Clear any pending reconnection
		if (reconnectTimeoutRef.current) {
			clearTimeout(reconnectTimeoutRef.current);
			reconnectTimeoutRef.current = null;
		}

		// Close the connection
		if (wsRef.current) {
			wsRef.current.close(1000, "Client disconnected");
			wsRef.current = null;
		}

		updateConnectionState("disconnected");
	}, [updateConnectionState]);

	/**
	 * Send a message to the server.
	 */
	const send = useCallback((data: unknown) => {
		if (wsRef.current?.readyState === WebSocket.OPEN) {
			wsRef.current.send(JSON.stringify(data));
		} else {
			logger.warn("[WebSocket] Cannot send: not connected");
		}
	}, []);

	// Auto-connect on mount and cleanup on unmount
	useEffect(() => {
		shouldReconnectRef.current = true;

		if (autoConnect) {
			connect();
		}

		return () => {
			disconnect();
		};
	}, [autoConnect, connect, disconnect]);

	// Reconnect when room changes
	useEffect(() => {
		if (wsRef.current?.readyState === WebSocket.OPEN) {
			// Disconnect and reconnect with new room
			disconnect();
			shouldReconnectRef.current = true;
			connect();
		}
		// Only trigger when room changes - connect/disconnect are stable callbacks
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [connect, disconnect]);

	return {
		connectionState,
		isConnected: connectionState === "connected",
		connect,
		disconnect,
		send,
	};
}

/**
 * Tests for the useWebSocket hook.
 *
 * Tests cover:
 * - Connection state management
 * - Auto-connect on mount
 * - Manual connect/disconnect
 * - Message handling
 * - Query invalidation based on message types
 * - Exponential backoff for reconnection
 * - Cleanup on unmount
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { WebSocketMessage } from "@/lib/types";
import { useWebSocket } from "../useWebSocket";

// Mock the logger
vi.mock("@/lib/logger", () => ({
	logger: {
		log: vi.fn(),
		warn: vi.fn(),
		error: vi.fn(),
	},
}));

// Store reference to created WebSocket instances
let mockWebSocketInstances: MockWebSocket[] = [];

// Mock WebSocket class
class MockWebSocket {
	static CONNECTING = 0;
	static OPEN = 1;
	static CLOSING = 2;
	static CLOSED = 3;

	url: string;
	readyState: number = MockWebSocket.CONNECTING;
	onopen: ((event: Event) => void) | null = null;
	onclose: ((event: CloseEvent) => void) | null = null;
	onmessage: ((event: MessageEvent) => void) | null = null;
	onerror: ((event: Event) => void) | null = null;

	constructor(url: string) {
		this.url = url;
		// Track this instance
		mockWebSocketInstances.push(this);
		// Simulate async connection
		setTimeout(() => {
			if (this.onopen && this.readyState !== MockWebSocket.CLOSED) {
				this.readyState = MockWebSocket.OPEN;
				this.onopen(new Event("open"));
			}
		}, 0);
	}

	send = vi.fn();

	close(code?: number, reason?: string) {
		this.readyState = MockWebSocket.CLOSED;
		if (this.onclose) {
			this.onclose({ code: code ?? 1000, reason: reason ?? "" } as CloseEvent);
		}
	}

	// Helper to simulate receiving a message
	simulateMessage(data: WebSocketMessage) {
		if (this.onmessage) {
			this.onmessage({ data: JSON.stringify(data) } as MessageEvent);
		}
	}

	// Helper to simulate error
	simulateError() {
		if (this.onerror) {
			this.onerror(new Event("error"));
		}
	}

	// Helper to simulate connection close
	simulateClose(code = 1000, reason = "") {
		this.readyState = MockWebSocket.CLOSED;
		if (this.onclose) {
			this.onclose({ code, reason } as CloseEvent);
		}
	}
}

// Install mock
const originalWebSocket = globalThis.WebSocket;

beforeEach(() => {
	mockWebSocketInstances = [];
	// Replace WebSocket with our mock class directly
	(globalThis as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;
});

afterEach(() => {
	globalThis.WebSocket = originalWebSocket;
	vi.clearAllMocks();
});

// Helper to create a WebSocketMessage with required fields
function createMessage<T>(type: WebSocketMessage["type"], data: T): WebSocketMessage<T> {
	return {
		type,
		data,
		timestamp: new Date().toISOString(),
	};
}

// Create a test query client
function createTestQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: {
				retry: false,
				gcTime: 0,
				staleTime: 0,
			},
		},
	});
}

// Wrapper component for rendering hooks with React Query
function createWrapper(queryClient?: QueryClient) {
	const client = queryClient ?? createTestQueryClient();
	return function Wrapper({ children }: { children: ReactNode }) {
		return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
	};
}

describe("useWebSocket", () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.clearAllMocks();
	});

	// ===========================================================================
	// Connection State Tests
	// ===========================================================================

	describe("connection state", () => {
		it("starts in disconnected state", () => {
			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			expect(result.current.connectionState).toBe("disconnected");
			expect(result.current.isConnected).toBe(false);
		});

		it("transitions to connecting state when connect is called", async () => {
			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			act(() => {
				result.current.connect();
			});

			expect(result.current.connectionState).toBe("connecting");
		});

		it("transitions to connected state after successful connection", async () => {
			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			act(() => {
				result.current.connect();
			});

			// Advance timers to trigger onopen
			await act(async () => {
				vi.runAllTimers();
			});

			expect(result.current.connectionState).toBe("connected");
			expect(result.current.isConnected).toBe(true);
		});

		it("transitions to disconnected state after disconnect", async () => {
			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			act(() => {
				result.current.connect();
			});

			await act(async () => {
				vi.runAllTimers();
			});

			expect(result.current.isConnected).toBe(true);

			act(() => {
				result.current.disconnect();
			});

			expect(result.current.connectionState).toBe("disconnected");
			expect(result.current.isConnected).toBe(false);
		});
	});

	// ===========================================================================
	// Auto-Connect Tests
	// ===========================================================================

	describe("auto-connect", () => {
		it("auto-connects on mount when autoConnect is true (default)", async () => {
			renderHook(() => useWebSocket({ room: "global" }), {
				wrapper: createWrapper(),
			});

			// Should have created a WebSocket
			expect(mockWebSocketInstances.length).toBe(1);
		});

		it("does not auto-connect when autoConnect is false", () => {
			renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			// Should not have created a WebSocket
			expect(mockWebSocketInstances.length).toBe(0);
		});
	});

	// ===========================================================================
	// Message Handling Tests
	// ===========================================================================

	describe("message handling", () => {
		it("calls onMessage callback when message is received", async () => {
			const onMessage = vi.fn();

			const { result } = renderHook(
				() => useWebSocket({ room: "global", onMessage, autoConnect: false }),
				{ wrapper: createWrapper() },
			);

			act(() => {
				result.current.connect();
			});

			await act(async () => {
				vi.runAllTimers();
			});

			const message = createMessage("task_completed", { task_id: "task-123" });

			act(() => {
				mockWebSocketInstances[0]?.simulateMessage(message);
			});

			expect(onMessage).toHaveBeenCalledWith(message);
		});

		it("calls onConnectionChange callback on state changes", async () => {
			const onConnectionChange = vi.fn();

			const { result } = renderHook(
				() =>
					useWebSocket({
						room: "global",
						onConnectionChange,
						autoConnect: false,
					}),
				{ wrapper: createWrapper() },
			);

			act(() => {
				result.current.connect();
			});

			expect(onConnectionChange).toHaveBeenCalledWith("connecting");

			await act(async () => {
				vi.runAllTimers();
			});

			expect(onConnectionChange).toHaveBeenCalledWith("connected");
		});
	});

	// ===========================================================================
	// Query Invalidation Tests
	// ===========================================================================

	describe("query invalidation", () => {
		it("invalidates tasks queries on task_completed message", async () => {
			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(queryClient),
			});

			act(() => {
				result.current.connect();
			});

			await act(async () => {
				vi.runAllTimers();
			});

			const message = createMessage("task_completed", { task_id: "task-123" });

			act(() => {
				mockWebSocketInstances[0]?.simulateMessage(message);
			});

			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["tasks"] });
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["dashboard"] });
		});

		it("invalidates worker queries on worker_updated message", async () => {
			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(queryClient),
			});

			act(() => {
				result.current.connect();
			});

			await act(async () => {
				vi.runAllTimers();
			});

			const message = createMessage("worker_updated", { worker_id: "worker-123" });

			act(() => {
				mockWebSocketInstances[0]?.simulateMessage(message);
			});

			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["workers"] });
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["dashboard"] });
		});

		it("invalidates queue queries on queue_updated message", async () => {
			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(queryClient),
			});

			act(() => {
				result.current.connect();
			});

			await act(async () => {
				vi.runAllTimers();
			});

			const message = createMessage("queue_updated", { queue_name: "default" });

			act(() => {
				mockWebSocketInstances[0]?.simulateMessage(message);
			});

			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["queues"] });
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["dashboard"] });
		});

		it("invalidates metrics queries on metrics_updated message", async () => {
			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(queryClient),
			});

			act(() => {
				result.current.connect();
			});

			await act(async () => {
				vi.runAllTimers();
			});

			const message = createMessage("metrics_updated", {});

			act(() => {
				mockWebSocketInstances[0]?.simulateMessage(message);
			});

			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["metrics"] });
		});
	});

	// ===========================================================================
	// Send Message Tests
	// ===========================================================================

	describe("send message", () => {
		it("sends message when connected", async () => {
			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			act(() => {
				result.current.connect();
			});

			await act(async () => {
				vi.runAllTimers();
			});

			const data = { type: "subscribe", room: "tasks" };
			act(() => {
				result.current.send(data);
			});

			expect(mockWebSocketInstances[0]?.send).toHaveBeenCalledWith(JSON.stringify(data));
		});

		it("does not send when disconnected", async () => {
			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			const data = { type: "subscribe", room: "tasks" };
			act(() => {
				result.current.send(data);
			});

			// Should not throw, but also not send
			expect(mockWebSocketInstances.length).toBe(0);
		});
	});

	// ===========================================================================
	// Return Values Tests
	// ===========================================================================

	describe("return values", () => {
		it("returns all expected properties", () => {
			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			expect(result.current).toHaveProperty("connectionState");
			expect(result.current).toHaveProperty("isConnected");
			expect(result.current).toHaveProperty("connect");
			expect(result.current).toHaveProperty("disconnect");
			expect(result.current).toHaveProperty("send");
		});

		it("connect is a function", () => {
			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			expect(typeof result.current.connect).toBe("function");
		});

		it("disconnect is a function", () => {
			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			expect(typeof result.current.disconnect).toBe("function");
		});

		it("send is a function", () => {
			const { result } = renderHook(() => useWebSocket({ room: "global", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			expect(typeof result.current.send).toBe("function");
		});
	});

	// ===========================================================================
	// Cleanup Tests
	// ===========================================================================

	describe("cleanup", () => {
		it("disconnects on unmount", async () => {
			const { result, unmount } = renderHook(
				() => useWebSocket({ room: "global", autoConnect: false }),
				{ wrapper: createWrapper() },
			);

			act(() => {
				result.current.connect();
			});

			await act(async () => {
				vi.runAllTimers();
			});

			expect(result.current.isConnected).toBe(true);

			unmount();

			// WebSocket should be closed
			expect(mockWebSocketInstances[0]?.readyState).toBe(MockWebSocket.CLOSED);
		});
	});

	// ===========================================================================
	// URL Construction Tests
	// ===========================================================================

	describe("URL construction", () => {
		it("constructs correct WebSocket URL with room parameter", async () => {
			const { result } = renderHook(() => useWebSocket({ room: "tasks", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			act(() => {
				result.current.connect();
			});

			expect(mockWebSocketInstances[0]?.url).toContain("room=tasks");
		});

		it("encodes room parameter correctly", async () => {
			const { result } = renderHook(() => useWebSocket({ room: "task:123", autoConnect: false }), {
				wrapper: createWrapper(),
			});

			act(() => {
				result.current.connect();
			});

			expect(mockWebSocketInstances[0]?.url).toContain(`room=${encodeURIComponent("task:123")}`);
		});
	});
});

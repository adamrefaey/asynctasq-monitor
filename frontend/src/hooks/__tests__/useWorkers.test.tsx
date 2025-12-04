/**
 * Tests for the useWorkers hooks.
 *
 * Tests cover:
 * - Worker list query hook
 * - Worker detail query hook
 * - Worker logs query hook
 * - Worker action mutations (pause, resume, shutdown, kill)
 * - Query key factory
 * - Prefetch and invalidation hooks
 * - Optimistic updates
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Worker, WorkerActionResponse, WorkerDetail, WorkerLogsResponse } from "@/lib/types";
import { createMockWorker } from "@/test/mocks";
import {
	useInvalidateWorkers,
	useKillWorker,
	usePauseWorker,
	usePrefetchWorker,
	useResumeWorker,
	useShutdownWorker,
	useWorker,
	useWorkerAction,
	useWorkerDetail,
	useWorkerLogs,
	useWorkers,
	workerKeys,
} from "../useWorkers";

// Mock the API module
vi.mock("@/lib/api", () => ({
	api: {
		getWorkers: vi.fn(),
		getWorkerById: vi.fn(),
		getWorkerDetail: vi.fn(),
		getWorkerLogs: vi.fn(),
		performWorkerAction: vi.fn(),
		pauseWorker: vi.fn(),
		resumeWorker: vi.fn(),
		shutdownWorker: vi.fn(),
		killWorker: vi.fn(),
	},
}));

import { api } from "@/lib/api";

// Create a test query client
function createTestQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: {
				retry: false,
				gcTime: 0,
				staleTime: 0,
			},
			mutations: {
				retry: false,
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

// Create mock worker detail
function createMockWorkerDetail(overrides: Partial<WorkerDetail> = {}): WorkerDetail {
	return {
		...createMockWorker(),
		recent_tasks: [],
		hourly_throughput: [],
		...overrides,
	};
}

// Create mock worker logs response
function createMockWorkerLogs(overrides: Partial<WorkerLogsResponse> = {}): WorkerLogsResponse {
	return {
		worker_id: "worker-1",
		logs: [
			{
				timestamp: "2025-12-04T10:00:00Z",
				level: "INFO",
				message: "Worker started",
			},
		],
		total: 1,
		has_more: false,
		...overrides,
	};
}

// Create mock worker action response
function createMockActionResponse(
	overrides: Partial<WorkerActionResponse> = {},
): WorkerActionResponse {
	return {
		success: true,
		message: "Action completed successfully",
		worker_id: "worker-123",
		action: "pause",
		...overrides,
	};
}

describe("useWorkers", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	// ===========================================================================
	// Query Key Factory Tests
	// ===========================================================================

	describe("workerKeys", () => {
		it("has correct base key", () => {
			expect(workerKeys.all).toEqual(["workers"]);
		});

		it("creates correct lists key", () => {
			expect(workerKeys.lists()).toEqual(["workers", "list"]);
		});

		it("creates correct list key with filters", () => {
			const filters = { status: "active" as const };
			expect(workerKeys.list(filters)).toEqual(["workers", "list", { filters }]);
		});

		it("creates correct list key without filters", () => {
			expect(workerKeys.list(undefined)).toEqual(["workers", "list", { filters: undefined }]);
		});

		it("creates correct details key", () => {
			expect(workerKeys.details()).toEqual(["workers", "detail"]);
		});

		it("creates correct detail key with id", () => {
			expect(workerKeys.detail("worker-123")).toEqual(["workers", "detail", "worker-123"]);
		});

		it("creates correct logs key", () => {
			expect(workerKeys.logs()).toEqual(["workers", "logs"]);
		});

		it("creates correct worker logs key with options", () => {
			const options = { level: "ERROR", limit: 50, offset: 0 };
			expect(workerKeys.workerLogs("worker-123", options)).toEqual([
				"workers",
				"logs",
				"worker-123",
				options,
			]);
		});
	});

	// ===========================================================================
	// useWorkers Query Tests
	// ===========================================================================

	describe("useWorkers query", () => {
		it("fetches workers successfully", async () => {
			const mockWorkers: Worker[] = [
				createMockWorker({ id: "worker-1" }),
				createMockWorker({ id: "worker-2" }),
			];
			vi.mocked(api.getWorkers).mockResolvedValue({
				items: mockWorkers,
				total: 2,
			});

			const { result } = renderHook(() => useWorkers(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data?.items).toEqual(mockWorkers);
			expect(api.getWorkers).toHaveBeenCalledWith(undefined);
		});

		it("applies filters correctly", async () => {
			const mockWorkers: Worker[] = [createMockWorker({ id: "worker-1", status: "active" })];
			vi.mocked(api.getWorkers).mockResolvedValue({
				items: mockWorkers,
				total: 1,
			});

			const filters = { status: "active" as const };
			const { result } = renderHook(() => useWorkers({ filters }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.getWorkers).toHaveBeenCalledWith(filters);
		});

		it("handles empty workers list", async () => {
			vi.mocked(api.getWorkers).mockResolvedValue({ items: [], total: 0 });

			const { result } = renderHook(() => useWorkers(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data?.items).toEqual([]);
		});

		it("handles error state", async () => {
			const error = new Error("Network error");
			vi.mocked(api.getWorkers).mockRejectedValue(error);

			const { result } = renderHook(() => useWorkers(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isError).toBe(true);
			});
		});
	});

	// ===========================================================================
	// useWorker Query Tests
	// ===========================================================================

	describe("useWorker query", () => {
		it("fetches single worker by id", async () => {
			const mockWorker = createMockWorker({ id: "worker-123" });
			vi.mocked(api.getWorkerById).mockResolvedValue(mockWorker);

			const { result } = renderHook(() => useWorker({ workerId: "worker-123" }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data).toEqual(mockWorker);
			expect(api.getWorkerById).toHaveBeenCalledWith("worker-123");
		});

		it("handles worker not found", async () => {
			const error = new Error("Worker not found");
			vi.mocked(api.getWorkerById).mockRejectedValue(error);

			const { result } = renderHook(() => useWorker({ workerId: "non-existent" }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isError).toBe(true);
			});
		});
	});

	// ===========================================================================
	// useWorkerDetail Query Tests
	// ===========================================================================

	describe("useWorkerDetail query", () => {
		it("fetches worker detail successfully", async () => {
			const mockDetail = createMockWorkerDetail({ id: "worker-123" });
			vi.mocked(api.getWorkerDetail).mockResolvedValue(mockDetail);

			const { result } = renderHook(() => useWorkerDetail({ workerId: "worker-123" }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data).toEqual(mockDetail);
			expect(api.getWorkerDetail).toHaveBeenCalledWith("worker-123");
		});
	});

	// ===========================================================================
	// useWorkerLogs Query Tests
	// ===========================================================================

	describe("useWorkerLogs query", () => {
		it("fetches worker logs successfully", async () => {
			const mockLogs = createMockWorkerLogs();
			vi.mocked(api.getWorkerLogs).mockResolvedValue(mockLogs);

			const { result } = renderHook(() => useWorkerLogs({ workerId: "worker-123" }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data).toEqual(mockLogs);
		});

		it("applies log filters correctly", async () => {
			const mockLogs = createMockWorkerLogs();
			vi.mocked(api.getWorkerLogs).mockResolvedValue(mockLogs);

			const { result } = renderHook(
				() =>
					useWorkerLogs({
						workerId: "worker-123",
						level: "ERROR",
						search: "timeout",
						limit: 50,
						offset: 10,
					}),
				{ wrapper: createWrapper() },
			);

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.getWorkerLogs).toHaveBeenCalledWith("worker-123", {
				level: "ERROR",
				search: "timeout",
				limit: 50,
				offset: 10,
			});
		});
	});

	// ===========================================================================
	// useWorkerAction Mutation Tests
	// ===========================================================================

	describe("useWorkerAction mutation", () => {
		it("performs pause action successfully", async () => {
			const mockResponse = createMockActionResponse({ action: "pause" });
			vi.mocked(api.performWorkerAction).mockResolvedValue(mockResponse);

			const { result } = renderHook(() => useWorkerAction(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ workerId: "worker-123", action: "pause" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.performWorkerAction).toHaveBeenCalledWith("worker-123", "pause", undefined);
		});

		it("performs resume action successfully", async () => {
			const mockResponse = createMockActionResponse({ action: "resume" });
			vi.mocked(api.performWorkerAction).mockResolvedValue(mockResponse);

			const { result } = renderHook(() => useWorkerAction(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ workerId: "worker-123", action: "resume" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});
		});

		it("performs kill action with force flag", async () => {
			const mockResponse = createMockActionResponse({ action: "kill" });
			vi.mocked(api.performWorkerAction).mockResolvedValue(mockResponse);

			const { result } = renderHook(() => useWorkerAction(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({
					workerId: "worker-123",
					action: "kill",
					force: true,
				});
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.performWorkerAction).toHaveBeenCalledWith("worker-123", "kill", true);
		});

		it("invalidates worker queries after action", async () => {
			const mockResponse = createMockActionResponse();
			vi.mocked(api.performWorkerAction).mockResolvedValue(mockResponse);

			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const { result } = renderHook(() => useWorkerAction(), {
				wrapper: createWrapper(queryClient),
			});

			await act(async () => {
				result.current.mutate({ workerId: "worker-123", action: "pause" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(invalidateSpy).toHaveBeenCalledWith({
				queryKey: workerKeys.all,
			});
		});
	});

	// ===========================================================================
	// usePauseWorker Mutation Tests
	// ===========================================================================

	describe("usePauseWorker mutation", () => {
		it("pauses a worker successfully", async () => {
			const mockResponse = createMockActionResponse({ action: "pause" });
			vi.mocked(api.pauseWorker).mockResolvedValue(mockResponse);

			const { result } = renderHook(() => usePauseWorker(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ workerId: "worker-123" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.pauseWorker).toHaveBeenCalledWith("worker-123");
		});

		it("handles pause error", async () => {
			const error = new Error("Cannot pause worker");
			vi.mocked(api.pauseWorker).mockRejectedValue(error);

			const { result } = renderHook(() => usePauseWorker(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ workerId: "worker-123" });
			});

			await waitFor(() => {
				expect(result.current.isError).toBe(true);
			});
		});
	});

	// ===========================================================================
	// useResumeWorker Mutation Tests
	// ===========================================================================

	describe("useResumeWorker mutation", () => {
		it("resumes a worker successfully", async () => {
			const mockResponse = createMockActionResponse({ action: "resume" });
			vi.mocked(api.resumeWorker).mockResolvedValue(mockResponse);

			const { result } = renderHook(() => useResumeWorker(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ workerId: "worker-123" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.resumeWorker).toHaveBeenCalledWith("worker-123");
		});
	});

	// ===========================================================================
	// useShutdownWorker Mutation Tests
	// ===========================================================================

	describe("useShutdownWorker mutation", () => {
		it("shuts down a worker successfully", async () => {
			const mockResponse = createMockActionResponse({ action: "shutdown" });
			vi.mocked(api.shutdownWorker).mockResolvedValue(mockResponse);

			const { result } = renderHook(() => useShutdownWorker(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ workerId: "worker-123" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.shutdownWorker).toHaveBeenCalledWith("worker-123");
		});
	});

	// ===========================================================================
	// useKillWorker Mutation Tests
	// ===========================================================================

	describe("useKillWorker mutation", () => {
		it("kills a worker successfully", async () => {
			const mockResponse = createMockActionResponse({ action: "kill" });
			vi.mocked(api.killWorker).mockResolvedValue(mockResponse);

			const { result } = renderHook(() => useKillWorker(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ workerId: "worker-123" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.killWorker).toHaveBeenCalledWith("worker-123", undefined);
		});

		it("kills a worker with force flag", async () => {
			const mockResponse = createMockActionResponse({ action: "kill" });
			vi.mocked(api.killWorker).mockResolvedValue(mockResponse);

			const { result } = renderHook(() => useKillWorker(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ workerId: "worker-123", force: true });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.killWorker).toHaveBeenCalledWith("worker-123", true);
		});
	});

	// ===========================================================================
	// usePrefetchWorker Tests
	// ===========================================================================

	describe("usePrefetchWorker", () => {
		it("returns a function", () => {
			const { result } = renderHook(() => usePrefetchWorker(), {
				wrapper: createWrapper(),
			});

			expect(typeof result.current).toBe("function");
		});

		it("prefetches worker detail when called", async () => {
			const mockDetail = createMockWorkerDetail({ id: "worker-123" });
			vi.mocked(api.getWorkerDetail).mockResolvedValue(mockDetail);

			const queryClient = createTestQueryClient();
			const prefetchSpy = vi.spyOn(queryClient, "prefetchQuery");

			const wrapper = ({ children }: { children: ReactNode }) => (
				<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
			);

			const { result } = renderHook(() => usePrefetchWorker(), { wrapper });

			// Call the prefetch function
			result.current("worker-123");

			expect(prefetchSpy).toHaveBeenCalledWith(
				expect.objectContaining({
					queryKey: workerKeys.detail("worker-123"),
				}),
			);
		});
	});

	// ===========================================================================
	// useInvalidateWorkers Tests
	// ===========================================================================

	describe("useInvalidateWorkers", () => {
		it("returns a function", () => {
			const { result } = renderHook(() => useInvalidateWorkers(), {
				wrapper: createWrapper(),
			});

			expect(typeof result.current).toBe("function");
		});

		it("invalidates worker queries when called", async () => {
			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const wrapper = ({ children }: { children: ReactNode }) => (
				<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
			);

			const { result } = renderHook(() => useInvalidateWorkers(), { wrapper });

			// Call the invalidate function
			result.current();

			expect(invalidateSpy).toHaveBeenCalledWith({
				queryKey: workerKeys.all,
			});
		});
	});
});

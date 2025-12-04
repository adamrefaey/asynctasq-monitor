/**
 * Tests for the useDashboard hooks.
 *
 * Tests cover:
 * - Dashboard summary hook
 * - Workers hook
 * - Worker detail hook
 * - Queues hook
 * - Queue detail hook
 * - Query key factory
 * - Invalidation hooks
 * - Prefetch hooks
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { QueueListResponse, Worker } from "@/lib/types";
import { createMockDashboardSummary, createMockQueue, createMockWorker } from "@/test/mocks";
import {
	dashboardKeys,
	useDashboardSummary,
	useInvalidateDashboard,
	usePrefetchQueue,
	usePrefetchWorker,
	useQueue,
	useQueues,
	useWorker,
	useWorkers,
} from "../useDashboard";

// Mock the API module
vi.mock("@/lib/api", () => ({
	api: {
		getDashboardSummary: vi.fn(),
		getWorkers: vi.fn(),
		getWorkerById: vi.fn(),
		getQueues: vi.fn(),
		getQueueByName: vi.fn(),
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
		},
	});
}

// Wrapper component for rendering hooks with React Query
function createWrapper() {
	const queryClient = createTestQueryClient();
	return function Wrapper({ children }: { children: ReactNode }) {
		return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
	};
}

describe("useDashboard", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	// ===========================================================================
	// Query Key Factory Tests
	// ===========================================================================

	describe("dashboardKeys", () => {
		it("has correct base key", () => {
			expect(dashboardKeys.all).toEqual(["dashboard"]);
		});

		it("creates correct summary key", () => {
			expect(dashboardKeys.summary()).toEqual(["dashboard", "summary"]);
		});

		it("creates correct workers key", () => {
			expect(dashboardKeys.workers()).toEqual(["dashboard", "workers"]);
		});

		it("creates correct worker key with id", () => {
			expect(dashboardKeys.worker("worker-123")).toEqual(["dashboard", "workers", "worker-123"]);
		});

		it("creates correct queues key", () => {
			expect(dashboardKeys.queues()).toEqual(["dashboard", "queues"]);
		});

		it("creates correct queue key with name", () => {
			expect(dashboardKeys.queue("emails")).toEqual(["dashboard", "queues", "emails"]);
		});
	});

	// ===========================================================================
	// useDashboardSummary Tests
	// ===========================================================================

	describe("useDashboardSummary", () => {
		it("fetches dashboard summary successfully", async () => {
			const mockSummary = createMockDashboardSummary();
			vi.mocked(api.getDashboardSummary).mockResolvedValue(mockSummary);

			const { result } = renderHook(() => useDashboardSummary(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data).toEqual(mockSummary);
			expect(api.getDashboardSummary).toHaveBeenCalledTimes(1);
		});

		it("handles error state", async () => {
			const error = new Error("Network error");
			vi.mocked(api.getDashboardSummary).mockRejectedValue(error);

			const { result } = renderHook(() => useDashboardSummary(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isError).toBe(true);
			});

			expect(result.current.error).toBeTruthy();
		});

		it("uses custom refetch interval", async () => {
			const mockSummary = createMockDashboardSummary();
			vi.mocked(api.getDashboardSummary).mockResolvedValue(mockSummary);

			const { result } = renderHook(() => useDashboardSummary({ refetchInterval: 5000 }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			// Hook should be configured with refetch interval
			expect(result.current.data).toEqual(mockSummary);
		});

		it("keeps previous data while refetching", async () => {
			const mockSummary1 = createMockDashboardSummary({ total_tasks: 100 });
			const mockSummary2 = createMockDashboardSummary({ total_tasks: 200 });

			vi.mocked(api.getDashboardSummary)
				.mockResolvedValueOnce(mockSummary1)
				.mockResolvedValueOnce(mockSummary2);

			const { result, rerender } = renderHook(() => useDashboardSummary(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.data?.total_tasks).toBe(100);
			});

			// Rerender to trigger potential refetch
			rerender();

			// Should still have data while potentially fetching
			expect(result.current.data).toBeTruthy();
		});
	});

	// ===========================================================================
	// useWorkers Tests
	// ===========================================================================

	describe("useWorkers (dashboard)", () => {
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

			expect(result.current.data).toEqual(mockWorkers);
		});

		it("handles empty workers list", async () => {
			vi.mocked(api.getWorkers).mockResolvedValue({ items: [], total: 0 });

			const { result } = renderHook(() => useWorkers(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data).toEqual([]);
		});
	});

	// ===========================================================================
	// useWorker Tests
	// ===========================================================================

	describe("useWorker (dashboard)", () => {
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
	// useQueues Tests
	// ===========================================================================

	describe("useQueues", () => {
		it("fetches queues successfully", async () => {
			const mockQueues: QueueListResponse = {
				items: [createMockQueue({ name: "default" }), createMockQueue({ name: "emails" })],
				total: 2,
			};
			vi.mocked(api.getQueues).mockResolvedValue(mockQueues);

			const { result } = renderHook(() => useQueues(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data).toEqual(mockQueues);
		});

		it("uses custom refetch interval", async () => {
			const mockQueues: QueueListResponse = {
				items: [createMockQueue()],
				total: 1,
			};
			vi.mocked(api.getQueues).mockResolvedValue(mockQueues);

			const { result } = renderHook(() => useQueues({ refetchInterval: 3000 }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data).toEqual(mockQueues);
		});
	});

	// ===========================================================================
	// useQueue Tests
	// ===========================================================================

	describe("useQueue", () => {
		it("fetches single queue by name", async () => {
			const mockQueue = createMockQueue({ name: "emails" });
			vi.mocked(api.getQueueByName).mockResolvedValue(mockQueue);

			const { result } = renderHook(() => useQueue({ queueName: "emails" }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data).toEqual(mockQueue);
			expect(api.getQueueByName).toHaveBeenCalledWith("emails");
		});

		it("handles queue not found", async () => {
			const error = new Error("Queue not found");
			vi.mocked(api.getQueueByName).mockRejectedValue(error);

			const { result } = renderHook(() => useQueue({ queueName: "non-existent" }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isError).toBe(true);
			});
		});
	});

	// ===========================================================================
	// useInvalidateDashboard Tests
	// ===========================================================================

	describe("useInvalidateDashboard", () => {
		it("returns a function", () => {
			const { result } = renderHook(() => useInvalidateDashboard(), {
				wrapper: createWrapper(),
			});

			expect(typeof result.current).toBe("function");
		});

		it("invalidates dashboard queries when called", async () => {
			const mockSummary = createMockDashboardSummary();
			vi.mocked(api.getDashboardSummary).mockResolvedValue(mockSummary);

			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const wrapper = ({ children }: { children: ReactNode }) => (
				<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
			);

			const { result } = renderHook(() => useInvalidateDashboard(), {
				wrapper,
			});

			// Call the invalidate function
			result.current();

			expect(invalidateSpy).toHaveBeenCalledWith({
				queryKey: dashboardKeys.all,
			});
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

		it("prefetches worker data when called", async () => {
			const mockWorker = createMockWorker({ id: "worker-123" });
			vi.mocked(api.getWorkerById).mockResolvedValue(mockWorker);

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
					queryKey: dashboardKeys.worker("worker-123"),
				}),
			);
		});
	});

	// ===========================================================================
	// usePrefetchQueue Tests
	// ===========================================================================

	describe("usePrefetchQueue", () => {
		it("returns a function", () => {
			const { result } = renderHook(() => usePrefetchQueue(), {
				wrapper: createWrapper(),
			});

			expect(typeof result.current).toBe("function");
		});

		it("prefetches queue data when called", async () => {
			const mockQueue = createMockQueue({ name: "emails" });
			vi.mocked(api.getQueueByName).mockResolvedValue(mockQueue);

			const queryClient = createTestQueryClient();
			const prefetchSpy = vi.spyOn(queryClient, "prefetchQuery");

			const wrapper = ({ children }: { children: ReactNode }) => (
				<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
			);

			const { result } = renderHook(() => usePrefetchQueue(), { wrapper });

			// Call the prefetch function
			result.current("emails");

			expect(prefetchSpy).toHaveBeenCalledWith(
				expect.objectContaining({
					queryKey: dashboardKeys.queue("emails"),
				}),
			);
		});
	});
});

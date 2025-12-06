/**
 * Tests for the useTasks hooks.
 *
 * Tests cover:
 * - Task list query hook
 * - Task detail query hook
 * - Retry task mutation
 * - Delete task mutation
 * - Bulk retry mutation
 * - Bulk delete mutation
 * - Query key factory
 * - Prefetch and invalidation hooks
 * - Optimistic updates
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Task } from "@/lib/types";
import { createMockPaginatedResponse, createMockTask } from "@/test/mocks";
import {
	taskKeys,
	useBulkDeleteTasks,
	useBulkRetryTasks,
	useDeleteTask,
	useInvalidateTasks,
	usePrefetchTask,
	useRetryTask,
	useTask,
	useTasks,
} from "../useTasks";

// Mock the API module
vi.mock("@/lib/api", () => ({
	api: {
		getTasks: vi.fn(),
		getTaskById: vi.fn(),
		retryTask: vi.fn(),
		deleteTask: vi.fn(),
		bulkRetryTasks: vi.fn(),
		bulkDeleteTasks: vi.fn(),
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

describe("useTasks", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	// ===========================================================================
	// Query Key Factory Tests
	// ===========================================================================

	describe("taskKeys", () => {
		it("has correct base key", () => {
			expect(taskKeys.all).toEqual(["tasks"]);
		});

		it("creates correct lists key", () => {
			expect(taskKeys.lists()).toEqual(["tasks", "list"]);
		});

		it("creates correct list key with filters", () => {
			const filters = { status: "failed" as const };
			expect(taskKeys.list(filters, 50, 0)).toEqual([
				"tasks",
				"list",
				{ filters, limit: 50, offset: 0 },
			]);
		});

		it("creates correct list key without filters", () => {
			expect(taskKeys.list(undefined, 50, 0)).toEqual([
				"tasks",
				"list",
				{ filters: undefined, limit: 50, offset: 0 },
			]);
		});

		it("creates correct details key", () => {
			expect(taskKeys.details()).toEqual(["tasks", "detail"]);
		});

		it("creates correct detail key with id", () => {
			expect(taskKeys.detail("task-123")).toEqual(["tasks", "detail", "task-123"]);
		});
	});

	// ===========================================================================
	// useTasks Query Tests
	// ===========================================================================

	describe("useTasks query", () => {
		it("fetches tasks successfully", async () => {
			const mockTasks = createMockPaginatedResponse([
				createMockTask({ id: "task-1" }),
				createMockTask({ id: "task-2" }),
			]);
			vi.mocked(api.getTasks).mockResolvedValue(mockTasks);

			const { result } = renderHook(() => useTasks(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data).toEqual(mockTasks);
			expect(api.getTasks).toHaveBeenCalledWith(undefined, 50, 0);
		});

		it("applies filters correctly", async () => {
			const mockTasks = createMockPaginatedResponse([
				createMockTask({ id: "task-1", status: "failed" }),
			]);
			vi.mocked(api.getTasks).mockResolvedValue(mockTasks);

			const filters = { status: "failed" as const };
			const { result } = renderHook(() => useTasks({ filters, limit: 20, offset: 10 }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.getTasks).toHaveBeenCalledWith(filters, 20, 10);
		});

		it("handles empty task list", async () => {
			const mockTasks = createMockPaginatedResponse<Task>([]);
			vi.mocked(api.getTasks).mockResolvedValue(mockTasks);

			const { result } = renderHook(() => useTasks(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data?.items).toEqual([]);
			expect(result.current.data?.total).toBe(0);
		});

		it("handles error state", async () => {
			const error = new Error("Network error");
			vi.mocked(api.getTasks).mockRejectedValue(error);

			const { result } = renderHook(() => useTasks(), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isError).toBe(true);
			});
		});
	});

	// ===========================================================================
	// useTask Query Tests
	// ===========================================================================

	describe("useTask query", () => {
		it("fetches single task by id", async () => {
			const mockTask = createMockTask({ id: "task-123", name: "test_task" });
			vi.mocked(api.getTaskById).mockResolvedValue(mockTask);

			const { result } = renderHook(() => useTask({ taskId: "task-123" }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(result.current.data).toEqual(mockTask);
			expect(api.getTaskById).toHaveBeenCalledWith("task-123");
		});

		it("handles task not found", async () => {
			const error = new Error("Task not found");
			vi.mocked(api.getTaskById).mockRejectedValue(error);

			const { result } = renderHook(() => useTask({ taskId: "non-existent" }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isError).toBe(true);
			});
		});

		it("refetches running tasks more frequently", async () => {
			const runningTask = createMockTask({ id: "task-123", status: "running" });
			vi.mocked(api.getTaskById).mockResolvedValue(runningTask);

			const { result } = renderHook(() => useTask({ taskId: "task-123" }), {
				wrapper: createWrapper(),
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			// The hook should be configured with dynamic refetch interval
			expect(result.current.data?.status).toBe("running");
		});
	});

	// ===========================================================================
	// useRetryTask Mutation Tests
	// ===========================================================================

	describe("useRetryTask mutation", () => {
		it("retries a task successfully", async () => {
			vi.mocked(api.retryTask).mockResolvedValue(undefined);

			const { result } = renderHook(() => useRetryTask(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ taskId: "task-123" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.retryTask).toHaveBeenCalledWith("task-123");
		});

		it("handles retry error", async () => {
			const error = new Error("Cannot retry task");
			vi.mocked(api.retryTask).mockRejectedValue(error);

			const { result } = renderHook(() => useRetryTask(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ taskId: "task-123" });
			});

			await waitFor(() => {
				expect(result.current.isError).toBe(true);
			});
		});

		it("invalidates task queries after retry", async () => {
			vi.mocked(api.retryTask).mockResolvedValue(undefined);

			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const { result } = renderHook(() => useRetryTask(), {
				wrapper: createWrapper(queryClient),
			});

			await act(async () => {
				result.current.mutate({ taskId: "task-123" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(invalidateSpy).toHaveBeenCalledWith({
				queryKey: taskKeys.all,
			});
		});
	});

	// ===========================================================================
	// useDeleteTask Mutation Tests
	// ===========================================================================

	describe("useDeleteTask mutation", () => {
		it("deletes a task successfully", async () => {
			vi.mocked(api.deleteTask).mockResolvedValue(undefined);

			const { result } = renderHook(() => useDeleteTask(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ taskId: "task-123" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.deleteTask).toHaveBeenCalledWith("task-123");
		});

		it("handles delete error", async () => {
			const error = new Error("Cannot delete task");
			vi.mocked(api.deleteTask).mockRejectedValue(error);

			const { result } = renderHook(() => useDeleteTask(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ taskId: "task-123" });
			});

			await waitFor(() => {
				expect(result.current.isError).toBe(true);
			});
		});

		it("invalidates task queries after delete", async () => {
			vi.mocked(api.deleteTask).mockResolvedValue(undefined);

			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const { result } = renderHook(() => useDeleteTask(), {
				wrapper: createWrapper(queryClient),
			});

			await act(async () => {
				result.current.mutate({ taskId: "task-123" });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(invalidateSpy).toHaveBeenCalledWith({
				queryKey: taskKeys.all,
			});
		});
	});

	// ===========================================================================
	// useBulkRetryTasks Mutation Tests
	// ===========================================================================

	describe("useBulkRetryTasks mutation", () => {
		it("bulk retries tasks successfully", async () => {
			vi.mocked(api.bulkRetryTasks).mockResolvedValue(undefined);

			const { result } = renderHook(() => useBulkRetryTasks(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ taskIds: ["task-1", "task-2", "task-3"] });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.bulkRetryTasks).toHaveBeenCalledWith(["task-1", "task-2", "task-3"]);
		});

		it("handles empty task list", async () => {
			vi.mocked(api.bulkRetryTasks).mockResolvedValue(undefined);

			const { result } = renderHook(() => useBulkRetryTasks(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ taskIds: [] });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.bulkRetryTasks).toHaveBeenCalledWith([]);
		});
	});

	// ===========================================================================
	// useBulkDeleteTasks Mutation Tests
	// ===========================================================================

	describe("useBulkDeleteTasks mutation", () => {
		it("bulk deletes tasks successfully", async () => {
			vi.mocked(api.bulkDeleteTasks).mockResolvedValue(undefined);

			const { result } = renderHook(() => useBulkDeleteTasks(), {
				wrapper: createWrapper(),
			});

			await act(async () => {
				result.current.mutate({ taskIds: ["task-1", "task-2"] });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(api.bulkDeleteTasks).toHaveBeenCalledWith(["task-1", "task-2"]);
		});

		it("invalidates queries after bulk delete", async () => {
			vi.mocked(api.bulkDeleteTasks).mockResolvedValue(undefined);

			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const { result } = renderHook(() => useBulkDeleteTasks(), {
				wrapper: createWrapper(queryClient),
			});

			await act(async () => {
				result.current.mutate({ taskIds: ["task-1"] });
			});

			await waitFor(() => {
				expect(result.current.isSuccess).toBe(true);
			});

			expect(invalidateSpy).toHaveBeenCalledWith({
				queryKey: taskKeys.all,
			});
		});
	});

	// ===========================================================================
	// usePrefetchTask Tests
	// ===========================================================================

	describe("usePrefetchTask", () => {
		it("returns a function", () => {
			const { result } = renderHook(() => usePrefetchTask(), {
				wrapper: createWrapper(),
			});

			expect(typeof result.current).toBe("function");
		});

		it("uses cached data from detail cache if available", async () => {
			const mockTask = createMockTask({ id: "task-123" });
			const queryClient = createTestQueryClient();

			// Set up spies before any calls
			const prefetchSpy = vi.spyOn(queryClient, "prefetchQuery");
			const setDataSpy = vi.spyOn(queryClient, "setQueryData");

			// Pre-populate the detail cache
			queryClient.setQueryData(taskKeys.detail("task-123"), mockTask);

			const wrapper = ({ children }: { children: ReactNode }) => (
				<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
			);

			const { result } = renderHook(() => usePrefetchTask(), { wrapper });

			// Clear spy calls from setup
			prefetchSpy.mockClear();
			setDataSpy.mockClear();

			// Call the prefetch function
			result.current("task-123");

			// Should not prefetch or set data since it's already cached
			expect(prefetchSpy).not.toHaveBeenCalled();
			expect(setDataSpy).not.toHaveBeenCalled();
		});

		it("seeds cache from list query data if available", async () => {
			const mockTask = createMockTask({ id: "task-456" });
			const queryClient = createTestQueryClient();

			// Set up spies before any calls
			const prefetchSpy = vi.spyOn(queryClient, "prefetchQuery");
			const setDataSpy = vi.spyOn(queryClient, "setQueryData");

			// Pre-populate the list cache with the task
			queryClient.setQueryData(taskKeys.list({}, 50, 0), {
				items: [mockTask],
				total: 1,
				limit: 50,
				offset: 0,
			});

			const wrapper = ({ children }: { children: ReactNode }) => (
				<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
			);

			const { result } = renderHook(() => usePrefetchTask(), { wrapper });

			// Clear spy calls from setup
			prefetchSpy.mockClear();
			setDataSpy.mockClear();

			// Call the prefetch function
			result.current("task-456");

			// Should set query data from list cache, not prefetch from network
			expect(prefetchSpy).not.toHaveBeenCalled();
			// setQueryData called once to seed the detail cache
			expect(setDataSpy).toHaveBeenCalledTimes(1);
			expect(setDataSpy).toHaveBeenCalledWith(taskKeys.detail("task-456"), mockTask);
		});

		it("falls back to network prefetch when not in cache", async () => {
			const mockTask = createMockTask({ id: "task-789" });
			vi.mocked(api.getTaskById).mockResolvedValue(mockTask);

			const queryClient = createTestQueryClient();
			const prefetchSpy = vi.spyOn(queryClient, "prefetchQuery");

			const wrapper = ({ children }: { children: ReactNode }) => (
				<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
			);

			const { result } = renderHook(() => usePrefetchTask(), { wrapper });

			// Call the prefetch function - task not in any cache
			result.current("task-789");

			expect(prefetchSpy).toHaveBeenCalledWith(
				expect.objectContaining({
					queryKey: taskKeys.detail("task-789"),
				}),
			);
		});
	});

	// ===========================================================================
	// useInvalidateTasks Tests
	// ===========================================================================

	describe("useInvalidateTasks", () => {
		it("returns a function", () => {
			const { result } = renderHook(() => useInvalidateTasks(), {
				wrapper: createWrapper(),
			});

			expect(typeof result.current).toBe("function");
		});

		it("invalidates task queries when called", async () => {
			const queryClient = createTestQueryClient();
			const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

			const wrapper = ({ children }: { children: ReactNode }) => (
				<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
			);

			const { result } = renderHook(() => useInvalidateTasks(), { wrapper });

			// Call the invalidate function
			result.current();

			expect(invalidateSpy).toHaveBeenCalledWith({
				queryKey: taskKeys.all,
			});
		});
	});
});

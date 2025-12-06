/**
 * TanStack Query v5 hooks for task operations.
 *
 * Follows best practices:
 * - Single object parameter signature
 * - Type-safe query keys with factory pattern
 * - Proper error handling with ApiError
 * - Optimistic updates for mutations
 * - Query invalidation patterns
 */

import {
	type QueryKey,
	type UseQueryOptions,
	useMutation,
	useQuery,
	useQueryClient,
} from "@tanstack/react-query";
import { type ApiError, api } from "@/lib/api";
import type { PaginatedResponse, Task, TaskFilters } from "@/lib/types";

// ============================================================================
// Query Key Factory
// ============================================================================

/**
 * Query key factory for type-safe, consistent cache keys.
 * Use this pattern to ensure cache invalidation works correctly.
 */
export const taskKeys = {
	/** Base key for all task queries */
	all: ["tasks"] as const,

	/** Key for task list queries */
	lists: () => [...taskKeys.all, "list"] as const,

	/** Key for task list with specific filters */
	list: (filters?: Partial<TaskFilters>, limit?: number, offset?: number) =>
		[...taskKeys.lists(), { filters, limit, offset }] as const,

	/** Key for all detail queries */
	details: () => [...taskKeys.all, "detail"] as const,

	/** Key for specific task detail */
	detail: (id: string) => [...taskKeys.details(), id] as const,
} as const;

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook options for useTasks query.
 */
interface UseTasksOptions {
	/** Task filters to apply */
	filters?: Partial<TaskFilters>;
	/** Number of items per page */
	limit?: number;
	/** Pagination offset */
	offset?: number;
	/** Additional query options */
	queryOptions?: Omit<
		UseQueryOptions<PaginatedResponse<Task>, ApiError, PaginatedResponse<Task>, QueryKey>,
		"queryKey" | "queryFn"
	>;
}

/**
 * Fetch paginated list of tasks with filters.
 *
 * @example
 * ```tsx
 * const { data, isPending, error } = useTasks({
 *   filters: { status: 'failed' },
 *   limit: 20,
 * });
 * ```
 */
export function useTasks({ filters, limit = 50, offset = 0, queryOptions }: UseTasksOptions = {}) {
	return useQuery({
		queryKey: taskKeys.list(filters, limit, offset),
		queryFn: () => api.getTasks(filters, limit, offset),
		// Refetch every 10 seconds for near-real-time updates
		refetchInterval: 10_000,
		// Keep previous data while fetching new data
		placeholderData: (previousData) => previousData,
		...queryOptions,
	});
}

/**
 * Hook options for useTask query.
 */
interface UseTaskOptions {
	/** Task ID to fetch */
	taskId: string;
	/** Additional query options */
	queryOptions?: Omit<UseQueryOptions<Task, ApiError, Task, QueryKey>, "queryKey" | "queryFn">;
}

/**
 * Fetch a single task by ID.
 *
 * @example
 * ```tsx
 * const { data: task, isPending, error } = useTask({
 *   taskId: 'abc-123',
 * });
 * ```
 */
export function useTask({ taskId, queryOptions }: UseTaskOptions) {
	return useQuery({
		queryKey: taskKeys.detail(taskId),
		queryFn: () => api.getTaskById(taskId),
		// Auto-refetch running tasks more frequently
		refetchInterval: (query) => {
			const task = query.state.data;
			if (task?.status === "running" || task?.status === "pending") {
				return 2_000; // 2 seconds for active tasks
			}
			return false; // No auto-refetch for completed tasks
		},
		...queryOptions,
	});
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Mutation context for optimistic updates.
 */
interface MutationContext {
	previousTask: Task | undefined;
	previousTasks: PaginatedResponse<Task> | undefined;
}

/**
 * Hook for retrying a failed task.
 *
 * @example
 * ```tsx
 * const { mutate: retryTask, isPending } = useRetryTask();
 * retryTask({ taskId: 'abc-123' });
 * ```
 */
export function useRetryTask() {
	const queryClient = useQueryClient();

	return useMutation<void, ApiError, { taskId: string }, MutationContext>({
		mutationFn: ({ taskId }) => api.retryTask(taskId),
		onMutate: async ({ taskId }) => {
			// Cancel any outgoing refetches
			await queryClient.cancelQueries({ queryKey: taskKeys.all });

			// Snapshot previous values for rollback
			const previousTask = queryClient.getQueryData<Task>(taskKeys.detail(taskId));
			const previousTasks = queryClient.getQueryData<PaginatedResponse<Task>>(taskKeys.lists());

			// Optimistically update the task status
			if (previousTask) {
				queryClient.setQueryData<Task>(taskKeys.detail(taskId), {
					...previousTask,
					status: "pending",
					attempt: previousTask.attempt + 1,
				});
			}

			return { previousTask, previousTasks };
		},
		onError: (_error, { taskId }, context) => {
			// Rollback on error
			if (context?.previousTask) {
				queryClient.setQueryData(taskKeys.detail(taskId), context.previousTask);
			}
		},
		onSettled: () => {
			// Invalidate all task queries to ensure consistency
			queryClient.invalidateQueries({ queryKey: taskKeys.all });
		},
	});
}

/**
 * Hook for deleting a task.
 *
 * @example
 * ```tsx
 * const { mutate: deleteTask, isPending } = useDeleteTask();
 * deleteTask({ taskId: 'abc-123' });
 * ```
 */
export function useDeleteTask() {
	const queryClient = useQueryClient();

	return useMutation<void, ApiError, { taskId: string }, MutationContext>({
		mutationFn: ({ taskId }) => api.deleteTask(taskId),
		onMutate: async ({ taskId }) => {
			// Cancel any outgoing refetches
			await queryClient.cancelQueries({ queryKey: taskKeys.all });

			// Snapshot previous values
			const previousTask = queryClient.getQueryData<Task>(taskKeys.detail(taskId));
			const previousTasks = queryClient.getQueryData<PaginatedResponse<Task>>(taskKeys.lists());

			// Optimistically remove from cache
			queryClient.removeQueries({ queryKey: taskKeys.detail(taskId) });

			return { previousTask, previousTasks };
		},
		onError: (_error, { taskId }, context) => {
			// Rollback on error
			if (context?.previousTask) {
				queryClient.setQueryData(taskKeys.detail(taskId), context.previousTask);
			}
			if (context?.previousTasks) {
				queryClient.setQueryData(taskKeys.lists(), context.previousTasks);
			}
		},
		onSettled: () => {
			// Invalidate to refetch current data
			queryClient.invalidateQueries({ queryKey: taskKeys.all });
		},
	});
}

/**
 * Hook for bulk retry of multiple tasks.
 *
 * @example
 * ```tsx
 * const { mutate: bulkRetry, isPending } = useBulkRetryTasks();
 * bulkRetry({ taskIds: ['abc-123', 'def-456'] });
 * ```
 */
export function useBulkRetryTasks() {
	const queryClient = useQueryClient();

	return useMutation<void, ApiError, { taskIds: string[] }>({
		mutationFn: ({ taskIds }) => api.bulkRetryTasks(taskIds),
		onSettled: () => {
			queryClient.invalidateQueries({ queryKey: taskKeys.all });
		},
	});
}

/**
 * Hook for bulk delete of multiple tasks.
 *
 * @example
 * ```tsx
 * const { mutate: bulkDelete, isPending } = useBulkDeleteTasks();
 * bulkDelete({ taskIds: ['abc-123', 'def-456'] });
 * ```
 */
export function useBulkDeleteTasks() {
	const queryClient = useQueryClient();

	return useMutation<void, ApiError, { taskIds: string[] }>({
		mutationFn: ({ taskIds }) => api.bulkDeleteTasks(taskIds),
		onSettled: () => {
			queryClient.invalidateQueries({ queryKey: taskKeys.all });
		},
	});
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Hook to prefetch task details for improved UX.
 *
 * Uses cache-first strategy: If task data is already in cache (from list queries),
 * it seeds the detail cache directly without making a network request.
 * This prevents 404 errors when using mock/sample data and improves performance.
 *
 * @example
 * ```tsx
 * const prefetchTask = usePrefetchTask();
 * // Prefetch on hover
 * <div onMouseEnter={() => prefetchTask(task.id)}>...</div>
 * ```
 */
export function usePrefetchTask() {
	const queryClient = useQueryClient();

	return (taskId: string) => {
		// Check if we already have this task in the detail cache
		const existingData = queryClient.getQueryData<Task>(taskKeys.detail(taskId));
		if (existingData) {
			return; // Already cached, no need to prefetch
		}

		// Try to find the task in any cached list queries
		const listQueries = queryClient.getQueriesData<PaginatedResponse<Task>>({
			queryKey: taskKeys.lists(),
		});

		for (const [, data] of listQueries) {
			const task = data?.items?.find((t) => t.id === taskId);
			if (task) {
				// Seed the detail cache with the task from the list
				queryClient.setQueryData(taskKeys.detail(taskId), task);
				return;
			}
		}

		// Fall back to network request only if not found in cache
		// Use void to explicitly ignore the promise (errors are silently discarded by TanStack Query)
		void queryClient.prefetchQuery({
			queryKey: taskKeys.detail(taskId),
			queryFn: () => api.getTaskById(taskId),
			staleTime: 5_000, // Consider data stale after 5 seconds
		});
	};
}

/**
 * Hook to invalidate all task queries.
 * Useful after WebSocket updates.
 *
 * @example
 * ```tsx
 * const invalidateTasks = useInvalidateTasks();
 * // Call when WS message received
 * invalidateTasks();
 * ```
 */
export function useInvalidateTasks() {
	const queryClient = useQueryClient();

	return () => {
		queryClient.invalidateQueries({ queryKey: taskKeys.all });
	};
}

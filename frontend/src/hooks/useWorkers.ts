/**
 * TanStack Query v5 hooks for worker operations.
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
import { useCallback } from "react";
import { type ApiError, api } from "@/lib/api";
import type {
	Worker,
	WorkerAction,
	WorkerActionResponse,
	WorkerDetail,
	WorkerFilters,
	WorkerLogsResponse,
} from "@/lib/types";

// ============================================================================
// Query Key Factory
// ============================================================================

/**
 * Query key factory for type-safe, consistent cache keys.
 * Use this pattern to ensure cache invalidation works correctly.
 */
export const workerKeys = {
	/** Base key for all worker queries */
	all: ["workers"] as const,

	/** Key for worker list queries */
	lists: () => [...workerKeys.all, "list"] as const,

	/** Key for worker list with specific filters */
	list: (filters?: Partial<WorkerFilters>) => [...workerKeys.lists(), { filters }] as const,

	/** Key for all detail queries */
	details: () => [...workerKeys.all, "detail"] as const,

	/** Key for specific worker detail */
	detail: (id: string) => [...workerKeys.details(), id] as const,

	/** Key for all log queries */
	logs: () => [...workerKeys.all, "logs"] as const,

	/** Key for specific worker logs */
	workerLogs: (
		id: string,
		options?: { level?: string; search?: string; limit?: number; offset?: number },
	) => [...workerKeys.logs(), id, options] as const,
} as const;

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Response type for workers list query.
 */
interface WorkersListResponse {
	items: Worker[];
	total: number;
}

/**
 * Hook options for useWorkers query.
 */
interface UseWorkersOptions {
	/** Worker filters to apply */
	filters?: Partial<WorkerFilters>;
	/** Additional query options */
	queryOptions?: Omit<
		UseQueryOptions<WorkersListResponse, ApiError, WorkersListResponse, QueryKey>,
		"queryKey" | "queryFn"
	>;
}

/**
 * Fetch list of workers with filters.
 *
 * @example
 * ```tsx
 * const { data, isPending, error } = useWorkers({
 *   filters: { status: 'active' },
 * });
 * ```
 */
export function useWorkers({ filters, queryOptions }: UseWorkersOptions = {}) {
	return useQuery({
		queryKey: workerKeys.list(filters),
		queryFn: () => api.getWorkers(filters),
		// Refetch every 5 seconds for near-real-time updates
		refetchInterval: 5_000,
		// Keep previous data while fetching new data
		placeholderData: (previousData) => previousData,
		...queryOptions,
	});
}

/**
 * Hook options for useWorker query.
 */
interface UseWorkerOptions {
	/** Worker ID to fetch */
	workerId: string;
	/** Additional query options */
	queryOptions?: Omit<UseQueryOptions<Worker, ApiError, Worker, QueryKey>, "queryKey" | "queryFn">;
}

/**
 * Fetch a single worker by ID.
 *
 * @example
 * ```tsx
 * const { data: worker, isPending, error } = useWorker({
 *   workerId: 'worker-001',
 * });
 * ```
 */
export function useWorker({ workerId, queryOptions }: UseWorkerOptions) {
	return useQuery({
		queryKey: workerKeys.detail(workerId),
		queryFn: () => api.getWorkerById(workerId),
		// Refetch every 5 seconds for status updates
		refetchInterval: 5_000,
		...queryOptions,
	});
}

/**
 * Hook options for useWorkerDetail query.
 */
interface UseWorkerDetailOptions {
	/** Worker ID to fetch */
	workerId: string;
	/** Additional query options */
	queryOptions?: Omit<
		UseQueryOptions<WorkerDetail, ApiError, WorkerDetail, QueryKey>,
		"queryKey" | "queryFn"
	>;
}

/**
 * Fetch detailed worker information including task history.
 *
 * @example
 * ```tsx
 * const { data: workerDetail, isPending } = useWorkerDetail({
 *   workerId: 'worker-001',
 * });
 * ```
 */
export function useWorkerDetail({ workerId, queryOptions }: UseWorkerDetailOptions) {
	return useQuery({
		queryKey: workerKeys.detail(workerId),
		queryFn: () => api.getWorkerDetail(workerId),
		// Refetch every 5 seconds for real-time updates
		refetchInterval: 5_000,
		...queryOptions,
	});
}

/**
 * Hook options for useWorkerLogs query.
 */
interface UseWorkerLogsOptions {
	/** Worker ID to fetch logs for */
	workerId: string;
	/** Log level filter */
	level?: string;
	/** Search term */
	search?: string;
	/** Maximum logs to return */
	limit?: number;
	/** Pagination offset */
	offset?: number;
	/** Additional query options */
	queryOptions?: Omit<
		UseQueryOptions<WorkerLogsResponse, ApiError, WorkerLogsResponse, QueryKey>,
		"queryKey" | "queryFn"
	>;
}

/**
 * Fetch logs from a worker.
 *
 * @example
 * ```tsx
 * const { data, isPending } = useWorkerLogs({
 *   workerId: 'worker-001',
 *   level: 'ERROR',
 *   limit: 50,
 * });
 * ```
 */
export function useWorkerLogs({
	workerId,
	level,
	search,
	limit = 100,
	offset = 0,
	queryOptions,
}: UseWorkerLogsOptions) {
	// Build options object, filtering out undefined values for exactOptionalPropertyTypes
	const logsOptions = {
		...(level !== undefined && { level }),
		...(search !== undefined && { search }),
		limit,
		offset,
	};

	return useQuery({
		queryKey: workerKeys.workerLogs(workerId, logsOptions),
		queryFn: () => api.getWorkerLogs(workerId, logsOptions),
		// Refetch every 3 seconds for live log streaming
		refetchInterval: 3_000,
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
	previousWorker: Worker | undefined;
	previousWorkers: WorkersListResponse | undefined;
}

/**
 * Hook for performing any worker action.
 *
 * @example
 * ```tsx
 * const { mutate: performAction, isPending } = useWorkerAction();
 * performAction({ workerId: 'worker-001', action: 'pause' });
 * ```
 */
export function useWorkerAction() {
	const queryClient = useQueryClient();

	return useMutation<
		WorkerActionResponse,
		ApiError,
		{ workerId: string; action: WorkerAction; force?: boolean },
		MutationContext
	>({
		mutationFn: ({ workerId, action, force }) => api.performWorkerAction(workerId, action, force),
		onMutate: async ({ workerId, action }) => {
			// Cancel any outgoing refetches
			await queryClient.cancelQueries({ queryKey: workerKeys.all });

			// Snapshot previous values for rollback
			const previousWorker = queryClient.getQueryData<Worker>(workerKeys.detail(workerId));
			const previousWorkers = queryClient.getQueryData<WorkersListResponse>(workerKeys.lists());

			// Optimistically update the worker status
			if (previousWorker) {
				const updatedWorker = { ...previousWorker };

				switch (action) {
					case "pause":
						updatedWorker.is_paused = true;
						break;
					case "resume":
						updatedWorker.is_paused = false;
						break;
					case "kill":
						updatedWorker.status = "offline";
						updatedWorker.current_task_id = null;
						updatedWorker.current_task_name = null;
						break;
					case "shutdown":
						// Shutdown is graceful, don't change status immediately
						break;
				}

				queryClient.setQueryData<Worker>(workerKeys.detail(workerId), updatedWorker);
			}

			return { previousWorker, previousWorkers };
		},
		onError: (_error, { workerId }, context) => {
			// Rollback on error
			if (context?.previousWorker) {
				queryClient.setQueryData(workerKeys.detail(workerId), context.previousWorker);
			}
		},
		onSettled: () => {
			// Invalidate all worker queries to ensure consistency
			queryClient.invalidateQueries({ queryKey: workerKeys.all });
		},
	});
}

/**
 * Hook for pausing a worker.
 *
 * @example
 * ```tsx
 * const { mutate: pauseWorker, isPending } = usePauseWorker();
 * pauseWorker({ workerId: 'worker-001' });
 * ```
 */
export function usePauseWorker() {
	const queryClient = useQueryClient();

	return useMutation<WorkerActionResponse, ApiError, { workerId: string }, MutationContext>({
		mutationFn: ({ workerId }) => api.pauseWorker(workerId),
		onMutate: async ({ workerId }) => {
			await queryClient.cancelQueries({ queryKey: workerKeys.all });
			const previousWorker = queryClient.getQueryData<Worker>(workerKeys.detail(workerId));
			const previousWorkers = queryClient.getQueryData<WorkersListResponse>(workerKeys.lists());

			if (previousWorker) {
				queryClient.setQueryData<Worker>(workerKeys.detail(workerId), {
					...previousWorker,
					is_paused: true,
				});
			}

			return { previousWorker, previousWorkers };
		},
		onError: (_error, { workerId }, context) => {
			if (context?.previousWorker) {
				queryClient.setQueryData(workerKeys.detail(workerId), context.previousWorker);
			}
		},
		onSettled: () => {
			queryClient.invalidateQueries({ queryKey: workerKeys.all });
		},
	});
}

/**
 * Hook for resuming a worker.
 *
 * @example
 * ```tsx
 * const { mutate: resumeWorker, isPending } = useResumeWorker();
 * resumeWorker({ workerId: 'worker-001' });
 * ```
 */
export function useResumeWorker() {
	const queryClient = useQueryClient();

	return useMutation<WorkerActionResponse, ApiError, { workerId: string }, MutationContext>({
		mutationFn: ({ workerId }) => api.resumeWorker(workerId),
		onMutate: async ({ workerId }) => {
			await queryClient.cancelQueries({ queryKey: workerKeys.all });
			const previousWorker = queryClient.getQueryData<Worker>(workerKeys.detail(workerId));
			const previousWorkers = queryClient.getQueryData<WorkersListResponse>(workerKeys.lists());

			if (previousWorker) {
				queryClient.setQueryData<Worker>(workerKeys.detail(workerId), {
					...previousWorker,
					is_paused: false,
				});
			}

			return { previousWorker, previousWorkers };
		},
		onError: (_error, { workerId }, context) => {
			if (context?.previousWorker) {
				queryClient.setQueryData(workerKeys.detail(workerId), context.previousWorker);
			}
		},
		onSettled: () => {
			queryClient.invalidateQueries({ queryKey: workerKeys.all });
		},
	});
}

/**
 * Hook for graceful shutdown of a worker.
 *
 * @example
 * ```tsx
 * const { mutate: shutdownWorker, isPending } = useShutdownWorker();
 * shutdownWorker({ workerId: 'worker-001' });
 * ```
 */
export function useShutdownWorker() {
	const queryClient = useQueryClient();

	return useMutation<WorkerActionResponse, ApiError, { workerId: string }>({
		mutationFn: ({ workerId }) => api.shutdownWorker(workerId),
		onSettled: () => {
			queryClient.invalidateQueries({ queryKey: workerKeys.all });
		},
	});
}

/**
 * Hook for immediately killing a worker.
 *
 * @example
 * ```tsx
 * const { mutate: killWorker, isPending } = useKillWorker();
 * killWorker({ workerId: 'worker-001', force: true });
 * ```
 */
export function useKillWorker() {
	const queryClient = useQueryClient();

	return useMutation<
		WorkerActionResponse,
		ApiError,
		{ workerId: string; force?: boolean },
		MutationContext
	>({
		mutationFn: ({ workerId, force }) => api.killWorker(workerId, force),
		onMutate: async ({ workerId }) => {
			await queryClient.cancelQueries({ queryKey: workerKeys.all });
			const previousWorker = queryClient.getQueryData<Worker>(workerKeys.detail(workerId));
			const previousWorkers = queryClient.getQueryData<WorkersListResponse>(workerKeys.lists());

			if (previousWorker) {
				queryClient.setQueryData<Worker>(workerKeys.detail(workerId), {
					...previousWorker,
					status: "offline",
					current_task_id: null,
					current_task_name: null,
				});
			}

			return { previousWorker, previousWorkers };
		},
		onError: (_error, { workerId }, context) => {
			if (context?.previousWorker) {
				queryClient.setQueryData(workerKeys.detail(workerId), context.previousWorker);
			}
		},
		onSettled: () => {
			queryClient.invalidateQueries({ queryKey: workerKeys.all });
		},
	});
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Hook to prefetch worker details for improved UX.
 *
 * @example
 * ```tsx
 * const prefetchWorker = usePrefetchWorker();
 * // Prefetch on hover
 * <div onMouseEnter={() => prefetchWorker(worker.id)}>...</div>
 * ```
 */
export function usePrefetchWorker() {
	const queryClient = useQueryClient();

	return useCallback(
		(workerId: string) => {
			queryClient.prefetchQuery({
				queryKey: workerKeys.detail(workerId),
				queryFn: () => api.getWorkerDetail(workerId),
				staleTime: 5_000, // Consider data stale after 5 seconds
			});
		},
		[queryClient],
	);
}

/**
 * Hook to invalidate all worker queries.
 * Useful after WebSocket updates.
 *
 * @example
 * ```tsx
 * const invalidateWorkers = useInvalidateWorkers();
 * // Call when WS message received
 * invalidateWorkers();
 * ```
 */
export function useInvalidateWorkers() {
	const queryClient = useQueryClient();

	return useCallback(() => {
		queryClient.invalidateQueries({ queryKey: workerKeys.all });
	}, [queryClient]);
}

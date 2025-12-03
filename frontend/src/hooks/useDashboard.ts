/**
 * TanStack Query v5 hooks for dashboard operations.
 *
 * Follows best practices:
 * - Single object parameter signature
 * - Type-safe query keys with factory pattern
 * - Auto-refresh for real-time data
 */

import {
	type QueryKey,
	type UseQueryOptions,
	useQuery,
	useQueryClient,
} from "@tanstack/react-query";
import { type ApiError, api } from "@/lib/api";
import type { DashboardSummary, Queue, Worker } from "@/lib/types";

// ============================================================================
// Query Key Factory
// ============================================================================

/**
 * Query key factory for dashboard-related queries.
 */
export const dashboardKeys = {
	/** Base key for all dashboard queries */
	all: ["dashboard"] as const,

	/** Key for dashboard summary */
	summary: () => [...dashboardKeys.all, "summary"] as const,

	/** Key for workers list */
	workers: () => [...dashboardKeys.all, "workers"] as const,

	/** Key for specific worker */
	worker: (id: string) => [...dashboardKeys.workers(), id] as const,

	/** Key for queues list */
	queues: () => [...dashboardKeys.all, "queues"] as const,

	/** Key for specific queue */
	queue: (name: string) => [...dashboardKeys.queues(), name] as const,
} as const;

// ============================================================================
// Dashboard Summary Hook
// ============================================================================

/**
 * Hook options for useDashboardSummary.
 */
interface UseDashboardSummaryOptions {
	/** Refresh interval in milliseconds (default: 10000) */
	refetchInterval?: number;
	/** Additional query options */
	queryOptions?: Omit<
		UseQueryOptions<DashboardSummary, ApiError, DashboardSummary, QueryKey>,
		"queryKey" | "queryFn"
	>;
}

/**
 * Fetch dashboard summary with auto-refresh.
 *
 * @example
 * ```tsx
 * const { data: summary, isPending } = useDashboardSummary({
 *   refetchInterval: 5000, // Refresh every 5 seconds
 * });
 * ```
 */
export function useDashboardSummary({
	refetchInterval = 10_000,
	queryOptions,
}: UseDashboardSummaryOptions = {}) {
	return useQuery({
		queryKey: dashboardKeys.summary(),
		queryFn: api.getDashboardSummary,
		refetchInterval,
		// Keep previous data visible while refetching
		placeholderData: (previousData) => previousData,
		...queryOptions,
	});
}

// ============================================================================
// Workers Hooks
// ============================================================================

/**
 * Hook options for useWorkers.
 */
interface UseWorkersOptions {
	/** Refresh interval in milliseconds */
	refetchInterval?: number;
	/** Additional query options */
	queryOptions?: Omit<
		UseQueryOptions<Worker[], ApiError, Worker[], QueryKey>,
		"queryKey" | "queryFn"
	>;
}

/**
 * Fetch all workers with auto-refresh.
 *
 * @example
 * ```tsx
 * const { data: workers, isPending } = useWorkers();
 * ```
 */
export function useWorkers({ refetchInterval = 5_000, queryOptions }: UseWorkersOptions = {}) {
	return useQuery({
		queryKey: dashboardKeys.workers(),
		queryFn: api.getWorkers,
		refetchInterval,
		placeholderData: (previousData) => previousData,
		...queryOptions,
	});
}

/**
 * Hook options for useWorker.
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
 * const { data: worker, isPending } = useWorker({ workerId: 'worker-1' });
 * ```
 */
export function useWorker({ workerId, queryOptions }: UseWorkerOptions) {
	return useQuery({
		queryKey: dashboardKeys.worker(workerId),
		queryFn: () => api.getWorkerById(workerId),
		refetchInterval: 5_000,
		...queryOptions,
	});
}

// ============================================================================
// Queues Hooks
// ============================================================================

/**
 * Hook options for useQueues.
 */
interface UseQueuesOptions {
	/** Refresh interval in milliseconds */
	refetchInterval?: number;
	/** Additional query options */
	queryOptions?: Omit<
		UseQueryOptions<Queue[], ApiError, Queue[], QueryKey>,
		"queryKey" | "queryFn"
	>;
}

/**
 * Fetch all queues with auto-refresh.
 *
 * @example
 * ```tsx
 * const { data: queues, isPending } = useQueues();
 * ```
 */
export function useQueues({ refetchInterval = 5_000, queryOptions }: UseQueuesOptions = {}) {
	return useQuery({
		queryKey: dashboardKeys.queues(),
		queryFn: api.getQueues,
		refetchInterval,
		placeholderData: (previousData) => previousData,
		...queryOptions,
	});
}

/**
 * Hook options for useQueue.
 */
interface UseQueueOptions {
	/** Queue name to fetch */
	queueName: string;
	/** Additional query options */
	queryOptions?: Omit<UseQueryOptions<Queue, ApiError, Queue, QueryKey>, "queryKey" | "queryFn">;
}

/**
 * Fetch a single queue by name.
 *
 * @example
 * ```tsx
 * const { data: queue, isPending } = useQueue({ queueName: 'emails' });
 * ```
 */
export function useQueue({ queueName, queryOptions }: UseQueueOptions) {
	return useQuery({
		queryKey: dashboardKeys.queue(queueName),
		queryFn: () => api.getQueueByName(queueName),
		refetchInterval: 5_000,
		...queryOptions,
	});
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Hook to invalidate all dashboard queries.
 * Useful after WebSocket updates.
 *
 * @example
 * ```tsx
 * const invalidateDashboard = useInvalidateDashboard();
 * // Call when WS message received
 * invalidateDashboard();
 * ```
 */
export function useInvalidateDashboard() {
	const queryClient = useQueryClient();

	return () => {
		queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
	};
}

/**
 * Hook to prefetch worker details for improved UX.
 *
 * @example
 * ```tsx
 * const prefetchWorker = usePrefetchWorker();
 * <div onMouseEnter={() => prefetchWorker(worker.id)}>...</div>
 * ```
 */
export function usePrefetchWorker() {
	const queryClient = useQueryClient();

	return (workerId: string) => {
		queryClient.prefetchQuery({
			queryKey: dashboardKeys.worker(workerId),
			queryFn: () => api.getWorkerById(workerId),
			staleTime: 5_000,
		});
	};
}

/**
 * Hook to prefetch queue details for improved UX.
 *
 * @example
 * ```tsx
 * const prefetchQueue = usePrefetchQueue();
 * <div onMouseEnter={() => prefetchQueue(queue.name)}>...</div>
 * ```
 */
export function usePrefetchQueue() {
	const queryClient = useQueryClient();

	return (queueName: string) => {
		queryClient.prefetchQuery({
			queryKey: dashboardKeys.queue(queueName),
			queryFn: () => api.getQueueByName(queueName),
			staleTime: 5_000,
		});
	};
}

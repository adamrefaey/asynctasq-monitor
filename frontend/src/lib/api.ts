/**
 * Type-safe API client for the async-task-q monitoring backend.
 * Follows best practices with proper error handling and type inference.
 */

import type {
	DashboardSummary,
	MetricsSummary,
	PaginatedResponse,
	Queue,
	QueueActionResponse,
	QueueClearResponse,
	QueueFilters,
	QueueListResponse,
	Task,
	TaskFilters,
	Worker,
	WorkerAction,
	WorkerActionResponse,
	WorkerDetail,
	WorkerFilters,
	WorkerLogsResponse,
} from "./types";

/** Base URL for API endpoints */
const API_BASE = "/api";

/**
 * Custom error class for API errors with status code.
 */
export class ApiError extends Error {
	status: number;
	detail: string | undefined;

	constructor(status: number, message: string, detail?: string) {
		super(message);
		this.name = "ApiError";
		this.status = status;
		this.detail = detail;
	}
}

/**
 * Type-safe fetch wrapper with error handling.
 */
async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
	const response = await fetch(`${API_BASE}${endpoint}`, {
		headers: {
			"Content-Type": "application/json",
			...options?.headers,
		},
		...options,
	});

	if (!response.ok) {
		let detail: string | undefined;
		try {
			const errorBody: unknown = await response.json();
			if (typeof errorBody === "object" && errorBody !== null && "detail" in errorBody) {
				detail = String((errorBody as { detail: unknown }).detail);
			}
		} catch {
			// Ignore JSON parsing errors
		}

		throw new ApiError(response.status, `HTTP ${response.status}: ${response.statusText}`, detail);
	}

	return response.json() as Promise<T>;
}

/**
 * Build URL search params from filters object.
 * Handles undefined values and arrays properly.
 */
function buildSearchParams(
	params: Record<string, string | number | boolean | string[] | undefined>,
): URLSearchParams {
	const searchParams = new URLSearchParams();

	for (const [key, value] of Object.entries(params)) {
		if (value === undefined) continue;

		if (Array.isArray(value)) {
			for (const item of value) {
				searchParams.append(key, item);
			}
		} else {
			searchParams.append(key, String(value));
		}
	}

	return searchParams;
}

/**
 * Type-safe API client with all monitoring endpoints.
 */
export const api = {
	// ============================================================================
	// Dashboard Endpoints
	// ============================================================================

	/**
	 * Get dashboard summary with all key metrics.
	 */
	getDashboardSummary: (): Promise<DashboardSummary> =>
		fetchApi<DashboardSummary>("/dashboard/summary"),

	// ============================================================================
	// Task Endpoints
	// ============================================================================

	/**
	 * List tasks with filtering and pagination.
	 */
	getTasks: (
		filters?: Partial<TaskFilters>,
		limit = 50,
		offset = 0,
	): Promise<PaginatedResponse<Task>> => {
		const params = buildSearchParams({
			status: filters?.status,
			queue: filters?.queue,
			worker_id: filters?.worker_id,
			search: filters?.search,
			from_date: filters?.from_date,
			to_date: filters?.to_date,
			tags: filters?.tags,
			limit,
			offset,
		});

		return fetchApi<PaginatedResponse<Task>>(`/tasks?${params.toString()}`);
	},

	/**
	 * Get a single task by ID.
	 */
	getTaskById: (taskId: string): Promise<Task> => {
		if (!taskId) {
			return Promise.reject(new ApiError(400, "Task ID is required"));
		}
		return fetchApi<Task>(`/tasks/${taskId}`);
	},

	/**
	 * Retry a failed task.
	 */
	retryTask: async (taskId: string): Promise<void> => {
		if (!taskId) {
			throw new ApiError(400, "Task ID is required");
		}
		await fetchApi<{ status: string; message: string }>(`/tasks/${taskId}/retry`, {
			method: "POST",
		});
	},

	/**
	 * Delete a task.
	 */
	deleteTask: async (taskId: string): Promise<void> => {
		if (!taskId) {
			throw new ApiError(400, "Task ID is required");
		}
		await fetchApi<{ status: string; message: string }>(`/tasks/${taskId}`, {
			method: "DELETE",
		});
	},

	/**
	 * Bulk retry multiple failed tasks.
	 */
	bulkRetryTasks: async (taskIds: string[]): Promise<void> => {
		await fetchApi<{ status: string; count: number }>("/tasks/bulk/retry", {
			method: "POST",
			body: JSON.stringify({ task_ids: taskIds }),
		});
	},

	/**
	 * Bulk delete multiple tasks.
	 */
	bulkDeleteTasks: async (taskIds: string[]): Promise<void> => {
		await fetchApi<{ status: string; count: number }>("/tasks/bulk/delete", {
			method: "POST",
			body: JSON.stringify({ task_ids: taskIds }),
		});
	},

	// ============================================================================
	// Worker Endpoints
	// ============================================================================

	/**
	 * List all workers with their current status.
	 */
	getWorkers: (filters?: Partial<WorkerFilters>): Promise<{ items: Worker[]; total: number }> => {
		const params = buildSearchParams({
			status: filters?.status,
			queue: filters?.queue,
			search: filters?.search,
			is_paused: filters?.is_paused,
			has_current_task: filters?.has_current_task,
		});
		const queryString = params.toString();
		return fetchApi<{ items: Worker[]; total: number }>(
			`/workers${queryString ? `?${queryString}` : ""}`,
		);
	},

	/**
	 * Get a single worker by ID.
	 */
	getWorkerById: (workerId: string): Promise<Worker> => {
		if (!workerId) {
			return Promise.reject(new ApiError(400, "Worker ID is required"));
		}
		return fetchApi<Worker>(`/workers/${workerId}`);
	},

	/**
	 * Get detailed worker information including task history.
	 */
	getWorkerDetail: (workerId: string): Promise<WorkerDetail> => {
		if (!workerId) {
			return Promise.reject(new ApiError(400, "Worker ID is required"));
		}
		return fetchApi<WorkerDetail>(`/workers/${workerId}/detail`);
	},

	/**
	 * Perform an action on a worker.
	 */
	performWorkerAction: (
		workerId: string,
		action: WorkerAction,
		force = false,
	): Promise<WorkerActionResponse> => {
		if (!workerId) {
			return Promise.reject(new ApiError(400, "Worker ID is required"));
		}
		return fetchApi<WorkerActionResponse>(`/workers/${workerId}/action`, {
			method: "POST",
			body: JSON.stringify({ action, force }),
		});
	},

	/**
	 * Pause a worker (stop accepting new tasks).
	 */
	pauseWorker: async (workerId: string): Promise<WorkerActionResponse> => {
		if (!workerId) {
			throw new ApiError(400, "Worker ID is required");
		}
		return fetchApi<WorkerActionResponse>(`/workers/${workerId}/pause`, {
			method: "POST",
		});
	},

	/**
	 * Resume a paused worker.
	 */
	resumeWorker: async (workerId: string): Promise<WorkerActionResponse> => {
		if (!workerId) {
			throw new ApiError(400, "Worker ID is required");
		}
		return fetchApi<WorkerActionResponse>(`/workers/${workerId}/resume`, {
			method: "POST",
		});
	},

	/**
	 * Request graceful shutdown of a worker.
	 */
	shutdownWorker: async (workerId: string): Promise<WorkerActionResponse> => {
		if (!workerId) {
			throw new ApiError(400, "Worker ID is required");
		}
		return fetchApi<WorkerActionResponse>(`/workers/${workerId}/shutdown`, {
			method: "POST",
		});
	},

	/**
	 * Immediately kill a worker.
	 */
	killWorker: async (workerId: string, force = false): Promise<WorkerActionResponse> => {
		if (!workerId) {
			throw new ApiError(400, "Worker ID is required");
		}
		const params = buildSearchParams({ force });
		return fetchApi<WorkerActionResponse>(`/workers/${workerId}/kill?${params.toString()}`, {
			method: "POST",
		});
	},

	/**
	 * Get logs from a worker.
	 */
	getWorkerLogs: (
		workerId: string,
		options?: {
			level?: string;
			search?: string;
			limit?: number;
			offset?: number;
		},
	): Promise<WorkerLogsResponse> => {
		if (!workerId) {
			return Promise.reject(new ApiError(400, "Worker ID is required"));
		}
		const params = buildSearchParams({
			level: options?.level,
			search: options?.search,
			limit: options?.limit,
			offset: options?.offset,
		});
		const queryString = params.toString();
		return fetchApi<WorkerLogsResponse>(
			`/workers/${workerId}/logs${queryString ? `?${queryString}` : ""}`,
		);
	},

	// ============================================================================
	// Queue Endpoints
	// ============================================================================

	/**
	 * List all queues with their statistics.
	 */
	getQueues: (filters?: Partial<QueueFilters>): Promise<QueueListResponse> => {
		const params = buildSearchParams({
			status: filters?.status,
			search: filters?.search,
			min_depth: filters?.min_depth,
			alert_level: filters?.alert_level,
		});
		const queryString = params.toString();
		return fetchApi<QueueListResponse>(`/queues${queryString ? `?${queryString}` : ""}`);
	},

	/**
	 * Get a single queue by name.
	 */
	getQueueByName: (queueName: string): Promise<Queue> => fetchApi<Queue>(`/queues/${queueName}`),

	/**
	 * Pause a queue (stop processing tasks).
	 */
	pauseQueue: async (queueName: string, reason?: string): Promise<QueueActionResponse> => {
		const options: RequestInit = { method: "POST" };
		if (reason) {
			options.body = JSON.stringify({ reason });
		}
		return fetchApi<QueueActionResponse>(`/queues/${queueName}/pause`, options);
	},

	/**
	 * Resume a paused queue.
	 */
	resumeQueue: async (queueName: string): Promise<QueueActionResponse> =>
		fetchApi<QueueActionResponse>(`/queues/${queueName}/resume`, {
			method: "POST",
		}),

	/**
	 * Clear all pending tasks from a queue.
	 */
	clearQueue: async (queueName: string): Promise<QueueClearResponse> =>
		fetchApi<QueueClearResponse>(`/queues/${queueName}`, {
			method: "DELETE",
		}),

	// ============================================================================
	// Metrics Endpoints
	// ============================================================================

	/**
	 * Get metrics summary with all chart data for a time range.
	 * @param timeRange - Time range like "1h", "6h", "24h", "7d", "30d"
	 */
	getMetricsSummary: (timeRange: string): Promise<MetricsSummary> =>
		fetchApi<MetricsSummary>(`/metrics/summary?time_range=${encodeURIComponent(timeRange)}`),

	/**
	 * Get throughput metrics over time.
	 */
	getThroughputMetrics: (params: {
		from: string;
		to: string;
		interval?: "1m" | "5m" | "15m" | "1h";
	}): Promise<Array<{ timestamp: string; completed: number; failed: number }>> => {
		const searchParams = buildSearchParams({
			from: params.from,
			to: params.to,
			interval: params.interval,
		});

		return fetchApi(`/metrics/throughput?${searchParams.toString()}`);
	},

	/**
	 * Get duration metrics over time.
	 */
	getDurationMetrics: (params: {
		from: string;
		to: string;
		queue?: string;
	}): Promise<
		Array<{
			timestamp: string;
			avg_ms: number;
			p50_ms: number;
			p95_ms: number;
			p99_ms: number;
		}>
	> => {
		const searchParams = buildSearchParams({
			from: params.from,
			to: params.to,
			queue: params.queue,
		});

		return fetchApi(`/metrics/duration?${searchParams.toString()}`);
	},
} as const;

// ============================================================================
// Convenience exports for direct function imports
// ============================================================================

/** Fetch dashboard summary */
export const fetchDashboardSummary = api.getDashboardSummary;

/** Fetch paginated tasks with filters */
export const fetchTasks = api.getTasks;

/** Fetch a single task by ID */
export const fetchTaskById = api.getTaskById;

/** Retry a failed task */
export const retryTask = api.retryTask;

/** Cancel/delete a task */
export const cancelTask = api.deleteTask;

/** Fetch all workers */
export const fetchWorkers = api.getWorkers;

/** Fetch a single worker */
export const fetchWorkerById = api.getWorkerById;

/** Fetch worker details with task history */
export const fetchWorkerDetail = api.getWorkerDetail;

/** Perform worker action */
export const performWorkerAction = api.performWorkerAction;

/** Pause a worker */
export const pauseWorker = api.pauseWorker;

/** Resume a worker */
export const resumeWorker = api.resumeWorker;

/** Shutdown a worker */
export const shutdownWorker = api.shutdownWorker;

/** Kill a worker */
export const killWorker = api.killWorker;

/** Fetch worker logs */
export const fetchWorkerLogs = api.getWorkerLogs;

/** Fetch all queues with stats */
export const fetchQueues = api.getQueues;

/** Fetch a single queue */
export const fetchQueueByName = api.getQueueByName;

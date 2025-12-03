/**
 * Core type definitions for the async-task-q monitoring UI.
 * These types match the backend API models.
 */

/**
 * Task execution status enum.
 * Matches backend TaskStatus enum.
 */
export type TaskStatus = "pending" | "running" | "completed" | "failed" | "retrying" | "cancelled";

/**
 * Complete task representation for monitoring.
 * All fields match the backend Task Pydantic model.
 */
export interface Task {
	/** Unique task ID (UUID) */
	id: string;
	/** Task function name (e.g., 'send_email') */
	name: string;
	/** Queue name task belongs to */
	queue: string;
	/** Current task status */
	status: TaskStatus;
	/** When task was added to queue (ISO string) */
	enqueued_at: string;
	/** When worker started processing (ISO string, null if not started) */
	started_at: string | null;
	/** When task finished (ISO string, null if not completed) */
	completed_at: string | null;
	/** Execution time in milliseconds (null if not completed) */
	duration_ms: number | null;
	/** Worker ID processing this task (null if not assigned) */
	worker_id: string | null;
	/** Current retry attempt number (starts at 1) */
	attempt: number;
	/** Maximum retry attempts allowed */
	max_retries: number;
	/** Positional arguments passed to the task */
	args: unknown[];
	/** Keyword arguments passed to the task */
	kwargs: Record<string, unknown>;
	/** Task return value if successful (null otherwise) */
	result: unknown | null;
	/** Exception message if failed (null otherwise) */
	exception: string | null;
	/** Full exception traceback if failed (null otherwise) */
	traceback: string | null;
	/** Task priority (higher = more important) */
	priority: number;
	/** Execution timeout in seconds (null if no timeout) */
	timeout_seconds: number | null;
	/** Custom tags for filtering */
	tags: string[];
}

/**
 * Filters for task list queries.
 */
export interface TaskFilters {
	/** Filter by task status */
	status?: TaskStatus | undefined;
	/** Filter by queue name */
	queue?: string | undefined;
	/** Filter by worker ID */
	worker_id?: string | undefined;
	/** Search in task name, ID, or arguments */
	search?: string | undefined;
	/** Filter tasks created after this date (ISO string) */
	from_date?: string | undefined;
	/** Filter tasks created before this date (ISO string) */
	to_date?: string | undefined;
	/** Filter by tags */
	tags?: string[] | undefined;
}

/**
 * Worker status enum.
 */
export type WorkerStatus = "active" | "idle" | "offline";

/**
 * Queue status enum.
 */
export type QueueStatus = "active" | "paused" | "draining";

/**
 * Worker information for monitoring.
 */
export interface Worker {
	/** Unique worker ID */
	id: string;
	/** Worker name (hostname or custom) */
	name: string;
	/** Current worker status */
	status: WorkerStatus;
	/** Queues this worker is processing */
	queues: string[];
	/** ID of task currently being processed (null if idle) */
	currentTask: string | null;
	/** Total tasks processed by this worker */
	tasksProcessed: number;
	/** Worker uptime in seconds */
	uptime_seconds: number;
	/** Last heartbeat timestamp (ISO string) */
	lastHeartbeat: string;
	/** CPU usage percentage (0-100) */
	cpuUsage?: number;
	/** Memory usage percentage (0-100) */
	memoryUsage?: number;
}

/**
 * Queue statistics for monitoring.
 */
export interface QueueStats {
	/** Queue name */
	name: string;
	/** Number of pending tasks */
	depth: number;
	/** Number of currently running tasks */
	processing: number;
	/** Total completed tasks */
	completed_total: number;
	/** Total failed tasks */
	failed_total: number;
	/** Average task duration in milliseconds */
	avg_duration_ms: number | null;
	/** Tasks processed per minute */
	throughput_per_minute: number | null;
}

/**
 * Queue with status for management UI.
 */
export interface Queue {
	/** Queue name */
	name: string;
	/** Current queue status */
	status: QueueStatus;
	/** Number of pending tasks */
	size: number;
	/** Total processed tasks */
	processed: number;
	/** Total failed tasks */
	failed: number;
	/** Number of workers assigned to this queue */
	workers: number;
	/** Average processing time in seconds */
	avgProcessingTime: number;
}

/**
 * Dashboard summary statistics.
 */
export interface DashboardSummary {
	/** Total number of tasks across all queues */
	total_tasks: number;
	/** Number of currently running tasks */
	running_tasks: number;
	/** Number of pending tasks */
	pending_tasks: number;
	/** Number of completed tasks */
	completed_tasks: number;
	/** Number of failed tasks */
	failed_tasks: number;
	/** Overall success rate (0-100) */
	success_rate: number;
	/** List of queue statistics */
	queues: QueueStats[];
	/** List of active workers */
	workers: Worker[];
	/** Recent task activity */
	recent_activity: Task[];
}

/**
 * Paginated API response wrapper.
 */
export interface PaginatedResponse<T> {
	/** Array of items for current page */
	items: T[];
	/** Total number of items across all pages */
	total: number;
	/** Number of items per page */
	limit: number;
	/** Current offset (for cursor-based pagination) */
	offset: number;
}

/**
 * WebSocket message types for real-time updates.
 */
export type WebSocketMessageType =
	| "task_enqueued"
	| "task_started"
	| "task_completed"
	| "task_failed"
	| "task_updated"
	| "worker_updated"
	| "worker_started"
	| "worker_stopped"
	| "queue_updated"
	| "metrics_updated";

/**
 * WebSocket message structure.
 */
export interface WebSocketMessage<T = unknown> {
	/** Message type for event handling */
	type: WebSocketMessageType;
	/** Event data payload */
	data: T;
	/** Timestamp when event occurred (ISO string) */
	timestamp: string;
}

/**
 * API error response structure.
 */
export interface ApiError {
	/** HTTP status code */
	status: number;
	/** Error message */
	message: string;
	/** Additional error details */
	detail?: string | undefined;
}

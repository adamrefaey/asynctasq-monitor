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
 * Worker action type enum.
 */
export type WorkerAction = "pause" | "resume" | "shutdown" | "kill";

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
	/** Hostname where worker is running */
	hostname?: string | null;
	/** Process ID */
	pid?: number | null;
	/** Current worker status */
	status: WorkerStatus;
	/** Queues this worker is processing */
	queues: string[];
	/** ID of task currently being processed (null if idle) */
	current_task_id: string | null;
	/** Name of task currently being processed (null if idle) */
	current_task_name?: string | null;
	/** When current task started (ISO string, null if idle) */
	current_task_started_at?: string | null;
	/** Total tasks processed by this worker */
	tasks_processed: number;
	/** Total tasks failed by this worker */
	tasks_failed: number;
	/** Average task duration in milliseconds */
	avg_task_duration_ms?: number | null;
	/** Worker uptime in seconds */
	uptime_seconds: number;
	/** When worker started (ISO string) */
	started_at: string;
	/** Last heartbeat timestamp (ISO string) */
	last_heartbeat: string;
	/** CPU usage percentage (0-100) */
	cpu_usage?: number | null;
	/** Memory usage percentage (0-100) */
	memory_usage?: number | null;
	/** Memory in MB */
	memory_mb?: number | null;
	/** Worker version */
	version?: string | null;
	/** Custom tags */
	tags?: string[];
	/** Whether worker is paused */
	is_paused: boolean;
	/** Computed: is worker online (heartbeat within 2 minutes) */
	is_online: boolean;
	/** Computed: success rate percentage */
	success_rate: number;
	/** Computed: tasks per hour */
	tasks_per_hour: number;
	/** Computed: formatted uptime string */
	uptime_formatted: string;
	/** Computed: seconds since last heartbeat */
	seconds_since_heartbeat: number;
}

/**
 * Worker filters for list queries.
 */
export interface WorkerFilters {
	/** Filter by worker status */
	status?: WorkerStatus | undefined;
	/** Filter by queue name */
	queue?: string | undefined;
	/** Search in worker name, ID, or hostname */
	search?: string | undefined;
	/** Filter by paused state */
	is_paused?: boolean | undefined;
	/** Filter by whether worker has current task */
	has_current_task?: boolean | undefined;
}

/**
 * Task summary for worker detail view.
 */
export interface WorkerTask {
	/** Task ID */
	id: string;
	/** Task name */
	name: string;
	/** Queue name */
	queue: string;
	/** Task status */
	status: string;
	/** When task started (ISO string) */
	started_at: string;
	/** When task completed (ISO string, null if not completed) */
	completed_at?: string | null;
	/** Duration in milliseconds */
	duration_ms?: number | null;
}

/**
 * Extended worker information with task history.
 */
export interface WorkerDetail extends Worker {
	/** Recent tasks processed by this worker */
	recent_tasks: WorkerTask[];
	/** Hourly throughput data */
	hourly_throughput: Array<{ hour: string; count: number }>;
}

/**
 * Response from worker action endpoint.
 */
export interface WorkerActionResponse {
	/** Whether action was successful */
	success: boolean;
	/** Worker ID action was performed on */
	worker_id: string;
	/** Action that was performed */
	action: WorkerAction;
	/** Human-readable message */
	message: string;
}

/**
 * Worker log entry.
 */
export interface WorkerLog {
	/** Log timestamp (ISO string) */
	timestamp: string;
	/** Log level (INFO, WARNING, ERROR, DEBUG) */
	level: string;
	/** Log message */
	message: string;
	/** Logger name */
	logger_name?: string | null;
}

/**
 * Response from worker logs endpoint.
 */
export interface WorkerLogsResponse {
	/** Worker ID */
	worker_id: string;
	/** Log entries */
	logs: WorkerLog[];
	/** Total log count */
	total: number;
	/** Whether more logs are available */
	has_more: boolean;
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
 * Queue alert level enum.
 */
export type QueueAlertLevel = "normal" | "warning" | "critical";

/**
 * Queue with status for management UI.
 * Matches the backend Queue Pydantic model.
 */
export interface Queue {
	/** Queue name */
	name: string;
	/** Current queue status */
	status: QueueStatus;
	/** Number of pending tasks in queue */
	depth: number;
	/** Number of tasks currently being processed */
	processing: number;
	/** Total number of completed tasks */
	completed_total: number;
	/** Total number of failed tasks */
	failed_total: number;
	/** Number of workers assigned to this queue */
	workers_assigned: number;
	/** Average task duration in milliseconds */
	avg_duration_ms: number | null;
	/** Tasks processed per minute */
	throughput_per_minute: number | null;
	/** Queue priority (higher = more important) */
	priority: number;
	/** Default max retries for tasks in this queue */
	max_retries: number;
	/** When the queue was created (ISO string) */
	created_at: string | null;
	/** When the queue was paused (ISO string, null if not paused) */
	paused_at: string | null;
	/** Computed: alert level based on queue depth */
	alert_level: QueueAlertLevel;
	/** Computed: total tasks (pending + processing + completed + failed) */
	total_tasks: number;
	/** Computed: success rate percentage (0-100) */
	success_rate: number;
	/** Computed: average duration in seconds */
	avg_duration_seconds: number | null;
	/** Computed: whether queue has no pending or processing tasks */
	is_idle: boolean;
}

/**
 * Queue filters for list queries.
 */
export interface QueueFilters {
	/** Filter by queue status */
	status?: QueueStatus | undefined;
	/** Search in queue name */
	search?: string | undefined;
	/** Filter queues with depth >= this value */
	min_depth?: number | undefined;
	/** Filter by alert level */
	alert_level?: QueueAlertLevel | undefined;
}

/**
 * Response from queue list endpoint.
 */
export interface QueueListResponse {
	/** List of queues */
	items: Queue[];
	/** Total number of queues */
	total: number;
}

/**
 * Response from queue action endpoints.
 */
export interface QueueActionResponse {
	/** Whether action was successful */
	success: boolean;
	/** Queue name action was performed on */
	queue_name: string;
	/** Action that was performed */
	action: string;
	/** Human-readable message */
	message: string;
}

/**
 * Response from queue clear endpoint.
 */
export interface QueueClearResponse {
	/** Whether clear was successful */
	success: boolean;
	/** Queue name that was cleared */
	queue_name: string;
	/** Number of tasks cleared */
	tasks_cleared: number;
	/** Human-readable message */
	message: string;
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

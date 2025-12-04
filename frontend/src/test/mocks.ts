/**
 * Mock data factories for testing.
 *
 * Provides factory functions to create consistent mock data
 * for all types used in the frontend tests.
 */

import type {
	DashboardSummary,
	MetricsSummary,
	PaginatedResponse,
	Queue,
	QueueStats,
	Task,
	TaskStatus,
	Worker,
	WorkerStatus,
} from "@/lib/types";

/**
 * Create a mock Task with sensible defaults.
 */
export function createMockTask(overrides: Partial<Task> = {}): Task {
	return {
		id: `task-${Math.random().toString(36).slice(2, 10)}`,
		name: "test_task",
		queue: "default",
		status: "completed" as TaskStatus,
		enqueued_at: "2025-12-04T10:00:00Z",
		started_at: "2025-12-04T10:00:01Z",
		completed_at: "2025-12-04T10:00:02Z",
		duration_ms: 1000,
		worker_id: "worker-1",
		attempt: 1,
		max_retries: 3,
		args: [],
		kwargs: {},
		result: null,
		exception: null,
		traceback: null,
		priority: 0,
		timeout_seconds: null,
		tags: [],
		...overrides,
	};
}

/**
 * Create a mock Worker with sensible defaults.
 */
export function createMockWorker(overrides: Partial<Worker> = {}): Worker {
	return {
		id: `worker-${Math.random().toString(36).slice(2, 10)}`,
		name: "test-worker",
		hostname: "localhost",
		pid: 12345,
		status: "active" as WorkerStatus,
		queues: ["default"],
		current_task_id: null,
		current_task_name: null,
		current_task_started_at: null,
		tasks_processed: 100,
		tasks_failed: 5,
		avg_task_duration_ms: 500,
		uptime_seconds: 3600,
		started_at: "2025-12-04T09:00:00Z",
		last_heartbeat: new Date().toISOString(),
		cpu_usage: 25,
		memory_usage: 40,
		memory_mb: 256,
		version: "1.0.0",
		tags: [],
		is_paused: false,
		is_online: true,
		success_rate: 95,
		tasks_per_hour: 100,
		uptime_formatted: "1h 0m",
		seconds_since_heartbeat: 5,
		...overrides,
	};
}

/**
 * Create a mock Queue with sensible defaults.
 */
export function createMockQueue(overrides: Partial<Queue> = {}): Queue {
	return {
		name: "default",
		status: "active",
		depth: 10,
		processing: 3,
		completed_total: 500,
		failed_total: 5,
		workers_assigned: 2,
		avg_duration_ms: 150,
		throughput_per_minute: 12.5,
		priority: 0,
		max_retries: 3,
		created_at: "2025-12-01T00:00:00Z",
		paused_at: null,
		alert_level: "normal",
		total_tasks: 518,
		success_rate: 99.0,
		avg_duration_seconds: 0.15,
		is_idle: false,
		...overrides,
	};
}

/**
 * Create a mock QueueStats for dashboard.
 */
export function createMockQueueStats(overrides: Partial<QueueStats> = {}): QueueStats {
	return {
		name: "default",
		depth: 10,
		processing: 3,
		completed_total: 500,
		failed_total: 5,
		avg_duration_ms: 150,
		throughput_per_minute: 12.5,
		...overrides,
	};
}

/**
 * Create a mock MetricsSummary with sensible defaults.
 */
export function createMockMetricsSummary(overrides: Partial<MetricsSummary> = {}): MetricsSummary {
	return {
		time_range: "24h",
		throughput: [
			{ timestamp: "2025-12-04T00:00:00Z", completed: 100, failed: 5 },
			{ timestamp: "2025-12-04T01:00:00Z", completed: 120, failed: 3 },
			{ timestamp: "2025-12-04T02:00:00Z", completed: 80, failed: 8 },
		],
		duration: {
			avg_ms: 150,
			p50_ms: 100,
			p95_ms: 350,
			p99_ms: 500,
		},
		status_breakdown: {
			pending: 42,
			running: 5,
			completed: 1180,
			failed: 7,
		},
		queue_depth: [
			{ timestamp: "2025-12-04T00:00:00Z", default: 10, emails: 5 },
			{ timestamp: "2025-12-04T01:00:00Z", default: 15, emails: 8 },
		],
		queues: ["default", "emails"],
		...overrides,
	};
}

/**
 * Create a mock DashboardSummary with sensible defaults.
 */
export function createMockDashboardSummary(
	overrides: Partial<DashboardSummary> = {},
): DashboardSummary {
	return {
		total_tasks: 1234,
		running_tasks: 5,
		pending_tasks: 42,
		completed_tasks: 1180,
		failed_tasks: 7,
		success_rate: 99.4,
		queues: [createMockQueueStats({ name: "default" }), createMockQueueStats({ name: "emails" })],
		workers: [createMockWorker()],
		recent_activity: [
			createMockTask({ status: "completed" }),
			createMockTask({ status: "running" }),
		],
		...overrides,
	};
}

/**
 * Create a mock paginated response.
 */
export function createMockPaginatedResponse<T>(
	items: T[],
	total?: number,
	limit = 50,
	offset = 0,
): PaginatedResponse<T> {
	return {
		items,
		total: total ?? items.length,
		limit,
		offset,
	};
}

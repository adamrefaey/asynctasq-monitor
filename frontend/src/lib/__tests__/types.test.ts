/**
 * Tests for type definitions and type guards.
 *
 * While TypeScript types are compile-time only, these tests verify:
 * - Type guard functions (if any)
 * - Default values and type compatibility
 * - Type structure matches expected patterns
 */

import { describe, expect, it } from "vitest";
import type {
	DashboardSummary,
	DurationStats,
	MetricsSummary,
	PaginatedResponse,
	Queue,
	QueueAlertLevel,
	QueueStatus,
	StatusBreakdown,
	Task,
	TaskFilters,
	TaskStatus,
	ThroughputDataPoint,
	WebSocketMessage,
	WebSocketMessageType,
	Worker,
	WorkerAction,
	WorkerDetail,
	WorkerFilters,
	WorkerStatus,
} from "../types";

describe("Type definitions", () => {
	// ==========================================================================
	// TaskStatus type
	// ==========================================================================

	describe("TaskStatus", () => {
		it("accepts valid status values", () => {
			const statuses: TaskStatus[] = [
				"pending",
				"running",
				"completed",
				"failed",
				"retrying",
				"cancelled",
			];
			expect(statuses).toHaveLength(6);
		});

		it("matches expected task lifecycle", () => {
			// A task can be in these states
			const taskLifecycle: Record<TaskStatus, boolean> = {
				pending: true,
				running: true,
				completed: true,
				failed: true,
				retrying: true,
				cancelled: true,
			};
			expect(Object.keys(taskLifecycle)).toHaveLength(6);
		});
	});

	// ==========================================================================
	// Task type
	// ==========================================================================

	describe("Task", () => {
		it("has required fields", () => {
			const task: Task = {
				id: "task-123",
				name: "send_email",
				queue: "default",
				status: "completed",
				enqueued_at: "2025-01-01T00:00:00Z",
				started_at: "2025-01-01T00:00:01Z",
				completed_at: "2025-01-01T00:00:02Z",
				duration_ms: 1000,
				worker_id: "worker-1",
				attempt: 1,
				max_retries: 3,
				args: ["test@example.com", "Hello"],
				kwargs: { subject: "Test" },
				result: { sent: true },
				exception: null,
				traceback: null,
				priority: 0,
				timeout_seconds: 300,
				tags: ["email", "notification"],
			};

			expect(task.id).toBe("task-123");
			expect(task.name).toBe("send_email");
			expect(task.status).toBe("completed");
		});

		it("supports nullable fields for pending tasks", () => {
			const pendingTask: Task = {
				id: "task-456",
				name: "process_data",
				queue: "default",
				status: "pending",
				enqueued_at: "2025-01-01T00:00:00Z",
				started_at: null,
				completed_at: null,
				duration_ms: null,
				worker_id: null,
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
			};

			expect(pendingTask.started_at).toBeNull();
			expect(pendingTask.completed_at).toBeNull();
			expect(pendingTask.duration_ms).toBeNull();
		});

		it("supports failed task with exception info", () => {
			const failedTask: Task = {
				id: "task-789",
				name: "failing_task",
				queue: "default",
				status: "failed",
				enqueued_at: "2025-01-01T00:00:00Z",
				started_at: "2025-01-01T00:00:01Z",
				completed_at: "2025-01-01T00:00:02Z",
				duration_ms: 1000,
				worker_id: "worker-1",
				attempt: 3,
				max_retries: 3,
				args: [],
				kwargs: {},
				result: null,
				exception: "ValueError: Invalid input",
				traceback: "Traceback (most recent call last):\n  ...",
				priority: 0,
				timeout_seconds: null,
				tags: [],
			};

			expect(failedTask.exception).toBe("ValueError: Invalid input");
			expect(failedTask.traceback).toBeTruthy();
		});
	});

	// ==========================================================================
	// TaskFilters type
	// ==========================================================================

	describe("TaskFilters", () => {
		it("supports all filter fields as optional", () => {
			const emptyFilters: TaskFilters = {};
			const partialFilters: TaskFilters = { status: "failed" };
			const fullFilters: TaskFilters = {
				status: "running",
				queue: "emails",
				worker_id: "worker-1",
				search: "test",
				from_date: "2025-01-01",
				to_date: "2025-01-31",
				tags: ["urgent"],
			};

			expect(emptyFilters).toEqual({});
			expect(partialFilters.status).toBe("failed");
			expect(fullFilters.queue).toBe("emails");
		});
	});

	// ==========================================================================
	// WorkerStatus type
	// ==========================================================================

	describe("WorkerStatus", () => {
		it("accepts valid status values", () => {
			const statuses: WorkerStatus[] = ["active", "idle", "offline"];
			expect(statuses).toHaveLength(3);
		});
	});

	// ==========================================================================
	// Worker type
	// ==========================================================================

	describe("Worker", () => {
		it("has required computed fields", () => {
			const worker: Worker = {
				id: "worker-1",
				name: "worker-node-1",
				hostname: "node-1.example.com",
				pid: 12345,
				status: "active",
				queues: ["default", "priority"],
				current_task_id: "task-123",
				current_task_name: "process_order",
				current_task_started_at: "2025-01-01T00:00:00Z",
				tasks_processed: 1000,
				tasks_failed: 10,
				avg_task_duration_ms: 250,
				uptime_seconds: 86400,
				started_at: "2025-01-01T00:00:00Z",
				last_heartbeat: "2025-01-02T00:00:00Z",
				cpu_usage: 45,
				memory_usage: 60,
				memory_mb: 512,
				version: "1.2.3",
				tags: ["production"],
				is_paused: false,
				is_online: true,
				success_rate: 99,
				tasks_per_hour: 125,
				uptime_formatted: "1d 0h",
				seconds_since_heartbeat: 5,
			};

			expect(worker.is_online).toBe(true);
			expect(worker.success_rate).toBe(99);
			expect(worker.uptime_formatted).toBe("1d 0h");
		});

		it("supports idle worker with no current task", () => {
			const idleWorker: Worker = {
				id: "worker-2",
				name: "worker-idle",
				hostname: null,
				pid: null,
				status: "idle",
				queues: ["default"],
				current_task_id: null,
				current_task_name: null,
				current_task_started_at: null,
				tasks_processed: 500,
				tasks_failed: 2,
				avg_task_duration_ms: null,
				uptime_seconds: 3600,
				started_at: "2025-01-01T00:00:00Z",
				last_heartbeat: "2025-01-01T01:00:00Z",
				cpu_usage: null,
				memory_usage: null,
				memory_mb: null,
				version: null,
				tags: [],
				is_paused: false,
				is_online: true,
				success_rate: 99.6,
				tasks_per_hour: 500,
				uptime_formatted: "1h 0m",
				seconds_since_heartbeat: 30,
			};

			expect(idleWorker.current_task_id).toBeNull();
			expect(idleWorker.status).toBe("idle");
		});
	});

	// ==========================================================================
	// WorkerAction type
	// ==========================================================================

	describe("WorkerAction", () => {
		it("accepts valid action values", () => {
			const actions: WorkerAction[] = ["pause", "resume", "shutdown", "kill"];
			expect(actions).toHaveLength(4);
		});
	});

	// ==========================================================================
	// QueueStatus and QueueAlertLevel types
	// ==========================================================================

	describe("QueueStatus", () => {
		it("accepts valid status values", () => {
			const statuses: QueueStatus[] = ["active", "paused", "draining"];
			expect(statuses).toHaveLength(3);
		});
	});

	describe("QueueAlertLevel", () => {
		it("accepts valid alert levels", () => {
			const levels: QueueAlertLevel[] = ["normal", "warning", "critical"];
			expect(levels).toHaveLength(3);
		});
	});

	// ==========================================================================
	// Queue type
	// ==========================================================================

	describe("Queue", () => {
		it("has required and computed fields", () => {
			const queue: Queue = {
				name: "email-queue",
				status: "active",
				depth: 150,
				processing: 5,
				completed_total: 10000,
				failed_total: 50,
				workers_assigned: 3,
				avg_duration_ms: 120,
				throughput_per_minute: 25.5,
				priority: 1,
				max_retries: 3,
				created_at: "2025-01-01T00:00:00Z",
				paused_at: null,
				alert_level: "warning",
				total_tasks: 10205,
				success_rate: 99.5,
				avg_duration_seconds: 0.12,
				is_idle: false,
			};

			expect(queue.alert_level).toBe("warning");
			expect(queue.total_tasks).toBe(10205);
			expect(queue.is_idle).toBe(false);
		});

		it("supports paused queue with paused_at", () => {
			const pausedQueue: Queue = {
				name: "maintenance-queue",
				status: "paused",
				depth: 0,
				processing: 0,
				completed_total: 100,
				failed_total: 0,
				workers_assigned: 0,
				avg_duration_ms: null,
				throughput_per_minute: null,
				priority: 0,
				max_retries: 3,
				created_at: "2025-01-01T00:00:00Z",
				paused_at: "2025-01-02T00:00:00Z",
				alert_level: "normal",
				total_tasks: 100,
				success_rate: 100,
				avg_duration_seconds: null,
				is_idle: true,
			};

			expect(pausedQueue.paused_at).toBeTruthy();
			expect(pausedQueue.is_idle).toBe(true);
		});
	});

	// ==========================================================================
	// MetricsSummary type
	// ==========================================================================

	describe("MetricsSummary", () => {
		it("contains all chart data structures", () => {
			const metrics: MetricsSummary = {
				time_range: "24h",
				throughput: [
					{ timestamp: "2025-01-01T00:00:00Z", completed: 100, failed: 5 },
					{ timestamp: "2025-01-01T01:00:00Z", completed: 120, failed: 3 },
				],
				duration: {
					avg_ms: 150,
					p50_ms: 100,
					p95_ms: 300,
					p99_ms: 500,
				},
				status_breakdown: {
					pending: 10,
					running: 5,
					completed: 1000,
					failed: 20,
				},
				queue_depth: [
					{ timestamp: "2025-01-01T00:00:00Z", default: 10 },
					{ timestamp: "2025-01-01T01:00:00Z", default: 15 },
				],
				queues: ["default", "emails", "priority"],
			};

			expect(metrics.throughput).toHaveLength(2);
			expect(metrics.duration.p95_ms).toBe(300);
			expect(metrics.status_breakdown.completed).toBe(1000);
		});

		it("supports optional queue_depth and queues", () => {
			const minimalMetrics: MetricsSummary = {
				time_range: "1h",
				throughput: [],
				duration: { avg_ms: 0, p50_ms: 0, p95_ms: 0, p99_ms: 0 },
				status_breakdown: { pending: 0, running: 0, completed: 0, failed: 0 },
			};

			expect(minimalMetrics.queue_depth).toBeUndefined();
			expect(minimalMetrics.queues).toBeUndefined();
		});
	});

	// ==========================================================================
	// DurationStats type
	// ==========================================================================

	describe("DurationStats", () => {
		it("has all percentile fields", () => {
			const stats: DurationStats = {
				avg_ms: 150,
				p50_ms: 100,
				p95_ms: 300,
				p99_ms: 500,
			};

			expect(stats.avg_ms).toBe(150);
			expect(stats.p50_ms).toBeLessThan(stats.p95_ms);
			expect(stats.p95_ms).toBeLessThan(stats.p99_ms);
		});
	});

	// ==========================================================================
	// ThroughputDataPoint type
	// ==========================================================================

	describe("ThroughputDataPoint", () => {
		it("has timestamp and counts", () => {
			const point: ThroughputDataPoint = {
				timestamp: "2025-01-01T00:00:00Z",
				completed: 100,
				failed: 5,
			};

			expect(point.timestamp).toBeTruthy();
			expect(point.completed).toBe(100);
			expect(point.failed).toBe(5);
		});

		it("supports optional successRate", () => {
			const pointWithRate: ThroughputDataPoint = {
				timestamp: "2025-01-01T00:00:00Z",
				completed: 100,
				failed: 5,
				successRate: 95.24,
			};

			expect(pointWithRate.successRate).toBeCloseTo(95.24);
		});
	});

	// ==========================================================================
	// StatusBreakdown type
	// ==========================================================================

	describe("StatusBreakdown", () => {
		it("has all status counts", () => {
			const breakdown: StatusBreakdown = {
				pending: 10,
				running: 5,
				completed: 1000,
				failed: 20,
			};

			const total = breakdown.pending + breakdown.running + breakdown.completed + breakdown.failed;
			expect(total).toBe(1035);
		});
	});

	// ==========================================================================
	// PaginatedResponse type
	// ==========================================================================

	describe("PaginatedResponse", () => {
		it("wraps any item type", () => {
			const taskResponse: PaginatedResponse<Task> = {
				items: [],
				total: 100,
				limit: 50,
				offset: 0,
			};

			const workerResponse: PaginatedResponse<Worker> = {
				items: [],
				total: 10,
				limit: 10,
				offset: 0,
			};

			expect(taskResponse.total).toBe(100);
			expect(workerResponse.total).toBe(10);
		});

		it("supports pagination math", () => {
			const response: PaginatedResponse<unknown> = {
				items: Array(50).fill(null),
				total: 250,
				limit: 50,
				offset: 100,
			};

			const totalPages = Math.ceil(response.total / response.limit);
			const currentPage = Math.floor(response.offset / response.limit) + 1;

			expect(totalPages).toBe(5);
			expect(currentPage).toBe(3);
		});
	});

	// ==========================================================================
	// WebSocketMessage types
	// ==========================================================================

	describe("WebSocketMessageType", () => {
		it("covers all event types", () => {
			const types: WebSocketMessageType[] = [
				"task_enqueued",
				"task_started",
				"task_completed",
				"task_failed",
				"task_updated",
				"worker_updated",
				"worker_started",
				"worker_stopped",
				"queue_updated",
				"metrics_updated",
			];

			expect(types).toHaveLength(10);
		});
	});

	describe("WebSocketMessage", () => {
		it("has type, data, and timestamp", () => {
			const message: WebSocketMessage<{ task_id: string }> = {
				type: "task_completed",
				data: { task_id: "task-123" },
				timestamp: "2025-01-01T00:00:00Z",
			};

			expect(message.type).toBe("task_completed");
			expect(message.data.task_id).toBe("task-123");
		});

		it("supports unknown data type", () => {
			const genericMessage: WebSocketMessage = {
				type: "metrics_updated",
				data: { cpu: 50, memory: 75 },
				timestamp: "2025-01-01T00:00:00Z",
			};

			expect(genericMessage.data).toBeTruthy();
		});
	});

	// ==========================================================================
	// DashboardSummary type
	// ==========================================================================

	describe("DashboardSummary", () => {
		it("aggregates all dashboard data", () => {
			const summary: DashboardSummary = {
				total_tasks: 5000,
				running_tasks: 10,
				pending_tasks: 50,
				completed_tasks: 4900,
				failed_tasks: 40,
				success_rate: 99.2,
				queues: [
					{
						name: "default",
						depth: 25,
						processing: 5,
						completed_total: 3000,
						failed_total: 20,
						avg_duration_ms: 100,
						throughput_per_minute: 20,
					},
				],
				workers: [],
				recent_activity: [],
			};

			expect(summary.total_tasks).toBe(5000);
			expect(summary.queues).toHaveLength(1);
			expect(summary.success_rate).toBeCloseTo(99.2);
		});
	});

	// ==========================================================================
	// WorkerDetail type
	// ==========================================================================

	describe("WorkerDetail", () => {
		it("extends Worker with additional fields", () => {
			const detail: WorkerDetail = {
				// Worker fields
				id: "worker-1",
				name: "worker-node-1",
				hostname: "node-1",
				pid: 12345,
				status: "active",
				queues: ["default"],
				current_task_id: null,
				current_task_name: null,
				current_task_started_at: null,
				tasks_processed: 1000,
				tasks_failed: 10,
				avg_task_duration_ms: 100,
				uptime_seconds: 3600,
				started_at: "2025-01-01T00:00:00Z",
				last_heartbeat: "2025-01-01T01:00:00Z",
				cpu_usage: 30,
				memory_usage: 50,
				memory_mb: 256,
				version: "1.0.0",
				tags: [],
				is_paused: false,
				is_online: true,
				success_rate: 99,
				tasks_per_hour: 1000,
				uptime_formatted: "1h",
				seconds_since_heartbeat: 5,
				// WorkerDetail specific fields
				recent_tasks: [
					{
						id: "task-1",
						name: "process",
						queue: "default",
						status: "completed",
						started_at: "2025-01-01T00:00:00Z",
						completed_at: "2025-01-01T00:00:01Z",
						duration_ms: 1000,
					},
				],
				hourly_throughput: [
					{ hour: "00", count: 50 },
					{ hour: "01", count: 45 },
				],
			};

			expect(detail.recent_tasks).toHaveLength(1);
			expect(detail.hourly_throughput).toHaveLength(2);
		});
	});

	// ==========================================================================
	// WorkerFilters type
	// ==========================================================================

	describe("WorkerFilters", () => {
		it("supports all filter fields as optional", () => {
			const filters: WorkerFilters = {
				status: "active",
				queue: "default",
				search: "node",
				is_paused: false,
				has_current_task: true,
			};

			expect(filters.status).toBe("active");
			expect(filters.has_current_task).toBe(true);
		});

		it("allows empty filters", () => {
			const emptyFilters: WorkerFilters = {};
			expect(Object.keys(emptyFilters)).toHaveLength(0);
		});
	});
});

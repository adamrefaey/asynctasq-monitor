/**
 * Tests for the API client module.
 *
 * Uses Vitest's global fetch mocking pattern following best practices:
 * - Mock fetch globally before tests
 * - Reset mocks between tests
 * - Test both success and error scenarios
 * - Verify correct HTTP methods, headers, and payloads
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../api";

// Mock fetch globally
const mockFetch = vi.fn();
(globalThis as unknown as { fetch: typeof mockFetch }).fetch = mockFetch;

/**
 * Helper to get the URL from the first mock call.
 */
function getCalledUrl(): string {
	const calls = mockFetch.mock.calls;
	if (!calls[0]) throw new Error("No mock calls recorded");
	return calls[0][0] as string;
}

/**
 * Helper to create a mock Response object.
 */
function createMockResponse<T>(data: T, options: { ok?: boolean; status?: number } = {}) {
	const { ok = true, status = 200 } = options;
	return {
		ok,
		status,
		statusText: ok ? "OK" : "Error",
		json: () => Promise.resolve(data),
	};
}

/**
 * Helper to create an error response with detail.
 */
function createErrorResponse(status: number, detail?: string) {
	return {
		ok: false,
		status,
		statusText: "Error",
		json: () => Promise.resolve(detail ? { detail } : {}),
	};
}

describe("API Client", () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	// ==========================================================================
	// ApiError class tests
	// ==========================================================================

	describe("ApiError", () => {
		it("creates error with status and message", () => {
			const error = new ApiError(404, "Not Found");
			expect(error.status).toBe(404);
			expect(error.message).toBe("Not Found");
			expect(error.detail).toBeUndefined();
			expect(error.name).toBe("ApiError");
		});

		it("creates error with detail", () => {
			const error = new ApiError(400, "Bad Request", "Invalid task ID");
			expect(error.status).toBe(400);
			expect(error.message).toBe("Bad Request");
			expect(error.detail).toBe("Invalid task ID");
		});

		it("is instance of Error", () => {
			const error = new ApiError(500, "Server Error");
			expect(error).toBeInstanceOf(Error);
		});
	});

	// ==========================================================================
	// Dashboard endpoints
	// ==========================================================================

	describe("getDashboardSummary", () => {
		it("fetches dashboard summary from correct endpoint", async () => {
			const mockSummary = {
				total_tasks: 100,
				running_tasks: 5,
				pending_tasks: 10,
				completed_tasks: 80,
				failed_tasks: 5,
				success_rate: 94.1,
				queues: [],
				workers: [],
				recent_activity: [],
			};
			mockFetch.mockResolvedValue(createMockResponse(mockSummary));

			const result = await api.getDashboardSummary();

			expect(mockFetch).toHaveBeenCalledWith("/api/dashboard/summary", {
				headers: { "Content-Type": "application/json" },
			});
			expect(result).toEqual(mockSummary);
		});
	});

	// ==========================================================================
	// Task endpoints
	// ==========================================================================

	describe("getTasks", () => {
		it("fetches tasks with default pagination", async () => {
			const mockResponse = { items: [], total: 0, limit: 50, offset: 0 };
			mockFetch.mockResolvedValue(createMockResponse(mockResponse));

			await api.getTasks();

			expect(mockFetch).toHaveBeenCalledWith(
				expect.stringContaining("/api/tasks?"),
				expect.objectContaining({
					headers: { "Content-Type": "application/json" },
				}),
			);
			const url = getCalledUrl();
			expect(url).toContain("limit=50");
			expect(url).toContain("offset=0");
		});

		it("applies filters correctly", async () => {
			const mockResponse = { items: [], total: 0, limit: 50, offset: 0 };
			mockFetch.mockResolvedValue(createMockResponse(mockResponse));

			await api.getTasks(
				{
					status: "failed",
					queue: "emails",
					search: "test",
				},
				25,
				10,
			);

			const url = getCalledUrl();
			expect(url).toContain("status=failed");
			expect(url).toContain("queue=emails");
			expect(url).toContain("search=test");
			expect(url).toContain("limit=25");
			expect(url).toContain("offset=10");
		});

		it("handles array filters (tags)", async () => {
			const mockResponse = { items: [], total: 0, limit: 50, offset: 0 };
			mockFetch.mockResolvedValue(createMockResponse(mockResponse));

			await api.getTasks({ tags: ["urgent", "billing"] });

			const url = getCalledUrl();
			expect(url).toContain("tags=urgent");
			expect(url).toContain("tags=billing");
		});
	});

	describe("getTaskById", () => {
		it("fetches a single task by ID", async () => {
			const mockTask = { id: "task-123", name: "test_task" };
			mockFetch.mockResolvedValue(createMockResponse(mockTask));

			const result = await api.getTaskById("task-123");

			expect(mockFetch).toHaveBeenCalledWith("/api/tasks/task-123", {
				headers: { "Content-Type": "application/json" },
			});
			expect(result).toEqual(mockTask);
		});
	});

	describe("retryTask", () => {
		it("sends POST request to retry endpoint", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					status: "success",
					message: "Task queued for retry",
				}),
			);

			await api.retryTask("task-123");

			expect(mockFetch).toHaveBeenCalledWith("/api/tasks/task-123/retry", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
			});
		});
	});

	describe("deleteTask", () => {
		it("sends DELETE request to task endpoint", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({ status: "success", message: "Task deleted" }),
			);

			await api.deleteTask("task-123");

			expect(mockFetch).toHaveBeenCalledWith("/api/tasks/task-123", {
				method: "DELETE",
				headers: { "Content-Type": "application/json" },
			});
		});
	});

	describe("bulkRetryTasks", () => {
		it("sends POST request with task IDs", async () => {
			mockFetch.mockResolvedValue(createMockResponse({ status: "success", count: 3 }));

			await api.bulkRetryTasks(["task-1", "task-2", "task-3"]);

			expect(mockFetch).toHaveBeenCalledWith("/api/tasks/bulk/retry", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ task_ids: ["task-1", "task-2", "task-3"] }),
			});
		});
	});

	describe("bulkDeleteTasks", () => {
		it("sends POST request with task IDs for deletion", async () => {
			mockFetch.mockResolvedValue(createMockResponse({ status: "success", count: 2 }));

			await api.bulkDeleteTasks(["task-1", "task-2"]);

			expect(mockFetch).toHaveBeenCalledWith("/api/tasks/bulk/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ task_ids: ["task-1", "task-2"] }),
			});
		});
	});

	// ==========================================================================
	// Worker endpoints
	// ==========================================================================

	describe("getWorkers", () => {
		it("fetches workers without filters", async () => {
			const mockResponse = { items: [], total: 0 };
			mockFetch.mockResolvedValue(createMockResponse(mockResponse));

			await api.getWorkers();

			expect(mockFetch).toHaveBeenCalledWith("/api/workers", {
				headers: { "Content-Type": "application/json" },
			});
		});

		it("applies worker filters", async () => {
			const mockResponse = { items: [], total: 0 };
			mockFetch.mockResolvedValue(createMockResponse(mockResponse));

			await api.getWorkers({
				status: "active",
				queue: "default",
				is_paused: false,
			});

			const url = getCalledUrl();
			expect(url).toContain("status=active");
			expect(url).toContain("queue=default");
			expect(url).toContain("is_paused=false");
		});
	});

	describe("getWorkerById", () => {
		it("fetches worker by ID", async () => {
			const mockWorker = { id: "worker-1", name: "test-worker" };
			mockFetch.mockResolvedValue(createMockResponse(mockWorker));

			const result = await api.getWorkerById("worker-1");

			expect(mockFetch).toHaveBeenCalledWith("/api/workers/worker-1", {
				headers: { "Content-Type": "application/json" },
			});
			expect(result).toEqual(mockWorker);
		});
	});

	describe("getWorkerDetail", () => {
		it("fetches worker detail endpoint", async () => {
			const mockDetail = { id: "worker-1", recent_tasks: [] };
			mockFetch.mockResolvedValue(createMockResponse(mockDetail));

			await api.getWorkerDetail("worker-1");

			expect(mockFetch).toHaveBeenCalledWith("/api/workers/worker-1/detail", {
				headers: { "Content-Type": "application/json" },
			});
		});
	});

	describe("performWorkerAction", () => {
		it("sends worker action request", async () => {
			const mockResponse = {
				success: true,
				worker_id: "worker-1",
				action: "pause",
				message: "Worker paused",
			};
			mockFetch.mockResolvedValue(createMockResponse(mockResponse));

			const result = await api.performWorkerAction("worker-1", "pause");

			expect(mockFetch).toHaveBeenCalledWith("/api/workers/worker-1/action", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ action: "pause", force: false }),
			});
			expect(result).toEqual(mockResponse);
		});

		it("includes force flag when specified", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					success: true,
					worker_id: "worker-1",
					action: "kill",
					message: "",
				}),
			);

			await api.performWorkerAction("worker-1", "kill", true);

			expect(mockFetch).toHaveBeenCalledWith("/api/workers/worker-1/action", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ action: "kill", force: true }),
			});
		});
	});

	describe("pauseWorker", () => {
		it("sends pause request", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					success: true,
					worker_id: "worker-1",
					action: "pause",
					message: "",
				}),
			);

			await api.pauseWorker("worker-1");

			expect(mockFetch).toHaveBeenCalledWith("/api/workers/worker-1/pause", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
			});
		});
	});

	describe("resumeWorker", () => {
		it("sends resume request", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					success: true,
					worker_id: "worker-1",
					action: "resume",
					message: "",
				}),
			);

			await api.resumeWorker("worker-1");

			expect(mockFetch).toHaveBeenCalledWith("/api/workers/worker-1/resume", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
			});
		});
	});

	describe("shutdownWorker", () => {
		it("sends shutdown request", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					success: true,
					worker_id: "worker-1",
					action: "shutdown",
					message: "",
				}),
			);

			await api.shutdownWorker("worker-1");

			expect(mockFetch).toHaveBeenCalledWith("/api/workers/worker-1/shutdown", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
			});
		});
	});

	describe("killWorker", () => {
		it("sends kill request without force", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					success: true,
					worker_id: "worker-1",
					action: "kill",
					message: "",
				}),
			);

			await api.killWorker("worker-1");

			expect(mockFetch).toHaveBeenCalledWith(
				expect.stringContaining("/api/workers/worker-1/kill"),
				expect.objectContaining({ method: "POST" }),
			);
		});

		it("sends kill request with force", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					success: true,
					worker_id: "worker-1",
					action: "kill",
					message: "",
				}),
			);

			await api.killWorker("worker-1", true);

			const url = getCalledUrl();
			expect(url).toContain("force=true");
		});
	});

	describe("getWorkerLogs", () => {
		it("fetches worker logs with options", async () => {
			const mockLogs = {
				worker_id: "worker-1",
				logs: [],
				total: 0,
				has_more: false,
			};
			mockFetch.mockResolvedValue(createMockResponse(mockLogs));

			await api.getWorkerLogs("worker-1", { level: "ERROR", limit: 100 });

			const url = getCalledUrl();
			expect(url).toContain("/api/workers/worker-1/logs");
			expect(url).toContain("level=ERROR");
			expect(url).toContain("limit=100");
		});

		it("fetches logs without options", async () => {
			const mockLogs = {
				worker_id: "worker-1",
				logs: [],
				total: 0,
				has_more: false,
			};
			mockFetch.mockResolvedValue(createMockResponse(mockLogs));

			await api.getWorkerLogs("worker-1");

			expect(mockFetch).toHaveBeenCalledWith("/api/workers/worker-1/logs", {
				headers: { "Content-Type": "application/json" },
			});
		});
	});

	// ==========================================================================
	// Queue endpoints
	// ==========================================================================

	describe("getQueues", () => {
		it("fetches queues without filters", async () => {
			const mockResponse = { items: [], total: 0 };
			mockFetch.mockResolvedValue(createMockResponse(mockResponse));

			await api.getQueues();

			expect(mockFetch).toHaveBeenCalledWith("/api/queues", {
				headers: { "Content-Type": "application/json" },
			});
		});

		it("applies queue filters", async () => {
			const mockResponse = { items: [], total: 0 };
			mockFetch.mockResolvedValue(createMockResponse(mockResponse));

			await api.getQueues({
				status: "paused",
				min_depth: 10,
				alert_level: "warning",
			});

			const url = getCalledUrl();
			expect(url).toContain("status=paused");
			expect(url).toContain("min_depth=10");
			expect(url).toContain("alert_level=warning");
		});
	});

	describe("getQueueByName", () => {
		it("fetches queue by name", async () => {
			const mockQueue = { name: "emails", depth: 100 };
			mockFetch.mockResolvedValue(createMockResponse(mockQueue));

			const result = await api.getQueueByName("emails");

			expect(mockFetch).toHaveBeenCalledWith("/api/queues/emails", {
				headers: { "Content-Type": "application/json" },
			});
			expect(result).toEqual(mockQueue);
		});
	});

	describe("pauseQueue", () => {
		it("pauses queue without reason", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					success: true,
					queue_name: "emails",
					action: "pause",
					message: "",
				}),
			);

			await api.pauseQueue("emails");

			expect(mockFetch).toHaveBeenCalledWith("/api/queues/emails/pause", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
			});
		});

		it("pauses queue with reason", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					success: true,
					queue_name: "emails",
					action: "pause",
					message: "",
				}),
			);

			await api.pauseQueue("emails", "Maintenance window");

			expect(mockFetch).toHaveBeenCalledWith("/api/queues/emails/pause", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ reason: "Maintenance window" }),
			});
		});
	});

	describe("resumeQueue", () => {
		it("resumes a paused queue", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					success: true,
					queue_name: "emails",
					action: "resume",
					message: "",
				}),
			);

			await api.resumeQueue("emails");

			expect(mockFetch).toHaveBeenCalledWith("/api/queues/emails/resume", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
			});
		});
	});

	describe("clearQueue", () => {
		it("clears queue tasks", async () => {
			mockFetch.mockResolvedValue(
				createMockResponse({
					success: true,
					queue_name: "emails",
					tasks_cleared: 50,
					message: "",
				}),
			);

			const result = await api.clearQueue("emails");

			expect(mockFetch).toHaveBeenCalledWith("/api/queues/emails", {
				method: "DELETE",
				headers: { "Content-Type": "application/json" },
			});
			expect(result.tasks_cleared).toBe(50);
		});
	});

	// ==========================================================================
	// Metrics endpoints
	// ==========================================================================

	describe("getMetricsSummary", () => {
		it("fetches metrics with time range", async () => {
			const mockMetrics = {
				time_range: "24h",
				throughput: [],
				duration: { avg_ms: 100, p50_ms: 80, p95_ms: 200, p99_ms: 300 },
				status_breakdown: { pending: 0, running: 0, completed: 100, failed: 5 },
			};
			mockFetch.mockResolvedValue(createMockResponse(mockMetrics));

			const result = await api.getMetricsSummary("24h");

			expect(mockFetch).toHaveBeenCalledWith("/api/metrics/summary?time_range=24h", {
				headers: { "Content-Type": "application/json" },
			});
			expect(result).toEqual(mockMetrics);
		});

		it("encodes special characters in time range", async () => {
			mockFetch.mockResolvedValue(createMockResponse({ time_range: "custom" }));

			await api.getMetricsSummary("2024-01-01T00:00:00Z");

			const url = getCalledUrl();
			expect(url).toContain("time_range=2024-01-01T00%3A00%3A00Z");
		});
	});

	describe("getThroughputMetrics", () => {
		it("fetches throughput data with parameters", async () => {
			const mockData = [{ timestamp: "2024-01-01T00:00:00Z", completed: 100, failed: 5 }];
			mockFetch.mockResolvedValue(createMockResponse(mockData));

			await api.getThroughputMetrics({
				from: "2024-01-01T00:00:00Z",
				to: "2024-01-02T00:00:00Z",
				interval: "1h",
			});

			const url = getCalledUrl();
			expect(url).toContain("/api/metrics/throughput");
			expect(url).toContain("interval=1h");
		});
	});

	describe("getDurationMetrics", () => {
		it("fetches duration data with parameters", async () => {
			const mockData = [
				{
					timestamp: "2024-01-01T00:00:00Z",
					avg_ms: 100,
					p50_ms: 80,
					p95_ms: 200,
					p99_ms: 300,
				},
			];
			mockFetch.mockResolvedValue(createMockResponse(mockData));

			await api.getDurationMetrics({
				from: "2024-01-01T00:00:00Z",
				to: "2024-01-02T00:00:00Z",
				queue: "emails",
			});

			const url = getCalledUrl();
			expect(url).toContain("/api/metrics/duration");
			expect(url).toContain("queue=emails");
		});
	});

	// ==========================================================================
	// Error handling
	// ==========================================================================

	describe("error handling", () => {
		it("throws ApiError on non-ok response", async () => {
			mockFetch.mockResolvedValue(createErrorResponse(404, "Task not found"));

			await expect(api.getTaskById("invalid-id")).rejects.toThrow(ApiError);
		});

		it("includes status code in error", async () => {
			mockFetch.mockResolvedValue(createErrorResponse(404, "Task not found"));

			try {
				await api.getTaskById("invalid-id");
			} catch (error) {
				expect(error).toBeInstanceOf(ApiError);
				expect((error as ApiError).status).toBe(404);
			}
		});

		it("includes detail from response body", async () => {
			mockFetch.mockResolvedValue(createErrorResponse(400, "Invalid task status"));

			try {
				await api.retryTask("task-123");
			} catch (error) {
				expect((error as ApiError).detail).toBe("Invalid task status");
			}
		});

		it("handles response without detail gracefully", async () => {
			mockFetch.mockResolvedValue(createErrorResponse(500));

			try {
				await api.getDashboardSummary();
			} catch (error) {
				expect((error as ApiError).status).toBe(500);
				expect((error as ApiError).detail).toBeUndefined();
			}
		});

		it("handles JSON parsing errors in error response", async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 500,
				statusText: "Internal Server Error",
				json: () => Promise.reject(new Error("Invalid JSON")),
			});

			await expect(api.getDashboardSummary()).rejects.toThrow(ApiError);
		});
	});
});

/**
 * Tests for the Dashboard page component.
 *
 * Tests cover:
 * - Loading state
 * - Error state
 * - Successful data rendering
 * - Stats cards with correct values
 * - Empty state handling
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DashboardSummary } from "@/lib/types";
import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import Dashboard from "../Dashboard";

// Mock the API module
vi.mock("@/lib/api", () => ({
	api: {
		getDashboardSummary: vi.fn(),
	},
}));

// Import the mocked api after vi.mock
import { api } from "@/lib/api";

const mockDashboardData: DashboardSummary = {
	total_tasks: 1234,
	running_tasks: 5,
	pending_tasks: 42,
	completed_tasks: 1180,
	failed_tasks: 7,
	success_rate: 99.4,
	queues: [
		{
			name: "default",
			depth: 10,
			processing: 3,
			completed_total: 500,
			failed_total: 2,
			avg_duration_ms: 150,
			throughput_per_minute: 12.5,
		},
		{
			name: "emails",
			depth: 5,
			processing: 1,
			completed_total: 200,
			failed_total: 1,
			avg_duration_ms: 80,
			throughput_per_minute: 8.2,
		},
	],
	workers: [],
	recent_activity: [
		{
			id: "task-1",
			name: "send_email",
			queue: "emails",
			status: "completed",
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
		},
		{
			id: "task-2",
			name: "process_data",
			queue: "default",
			status: "running",
			enqueued_at: "2025-12-04T10:01:00Z",
			started_at: "2025-12-04T10:01:01Z",
			completed_at: null,
			duration_ms: null,
			worker_id: "worker-2",
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
		},
	],
};

describe("Dashboard", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("shows loading state initially", async () => {
		// Mock a pending promise that never resolves during this test
		vi.mocked(api.getDashboardSummary).mockImplementation(() => new Promise(() => {}));

		renderWithProviders(<Dashboard />);

		expect(screen.getByText("Loading dashboard...")).toBeInTheDocument();
	});

	it("renders stat cards with correct values", async () => {
		vi.mocked(api.getDashboardSummary).mockResolvedValue(mockDashboardData);

		renderWithProviders(<Dashboard />);

		await waitFor(() => {
			expect(screen.getByText("1,234")).toBeInTheDocument();
		});

		// Check all stat card values
		expect(screen.getByText("Total Tasks")).toBeInTheDocument();
		expect(screen.getByText("1,234")).toBeInTheDocument();

		expect(screen.getByText("Running")).toBeInTheDocument();
		expect(screen.getByText("5")).toBeInTheDocument();

		expect(screen.getByText("Success Rate")).toBeInTheDocument();
		expect(screen.getByText("99.4%")).toBeInTheDocument();

		expect(screen.getByText("Failed")).toBeInTheDocument();
		expect(screen.getByText("7")).toBeInTheDocument();
	});

	it("renders recent activity with task items", async () => {
		vi.mocked(api.getDashboardSummary).mockResolvedValue(mockDashboardData);

		renderWithProviders(<Dashboard />);

		await waitFor(() => {
			expect(screen.getByText("Recent Activity")).toBeInTheDocument();
		});

		// Check that recent activity tasks are displayed
		expect(screen.getByText("send_email")).toBeInTheDocument();
		expect(screen.getByText("process_data")).toBeInTheDocument();
	});

	it("renders queue health section with queue data", async () => {
		vi.mocked(api.getDashboardSummary).mockResolvedValue(mockDashboardData);

		renderWithProviders(<Dashboard />);

		await waitFor(() => {
			expect(screen.getByText("Queue Health")).toBeInTheDocument();
		});

		// Check queues are displayed in the Queue Health section
		// Use getAllByText since "default" appears both in Queue Health and Recent Activity
		const defaultElements = screen.getAllByText("default");
		expect(defaultElements.length).toBeGreaterThanOrEqual(1);

		const emailsElements = screen.getAllByText("emails");
		expect(emailsElements.length).toBeGreaterThanOrEqual(1);

		// Check pending counts - these are unique to Queue Health section
		expect(screen.getByText(/10\s*pending/)).toBeInTheDocument();
		expect(screen.getByText(/5\s*pending/)).toBeInTheDocument();
	});

	it("shows error state when API call fails", async () => {
		const errorMessage = "Network error";
		vi.mocked(api.getDashboardSummary).mockRejectedValue(new Error(errorMessage));

		renderWithProviders(<Dashboard />);

		await waitFor(() => {
			expect(screen.getByText("Failed to load dashboard")).toBeInTheDocument();
		});

		expect(screen.getByText(errorMessage)).toBeInTheDocument();
	});

	it("shows empty state when no queues or activity", async () => {
		const emptyData: DashboardSummary = {
			...mockDashboardData,
			queues: [],
			recent_activity: [],
		};
		vi.mocked(api.getDashboardSummary).mockResolvedValue(emptyData);

		renderWithProviders(<Dashboard />);

		await waitFor(() => {
			expect(screen.getByText("No recent activity")).toBeInTheDocument();
		});

		expect(screen.getByText("No queues configured")).toBeInTheDocument();
	});

	it("displays zero values correctly when no tasks exist", async () => {
		const zeroData: DashboardSummary = {
			total_tasks: 0,
			running_tasks: 0,
			pending_tasks: 0,
			completed_tasks: 0,
			failed_tasks: 0,
			success_rate: 0,
			queues: [],
			workers: [],
			recent_activity: [],
		};
		vi.mocked(api.getDashboardSummary).mockResolvedValue(zeroData);

		renderWithProviders(<Dashboard />);

		await waitFor(() => {
			// Multiple "0" values exist, so check at least one is present
			expect(screen.getAllByText("0")).toHaveLength(3); // Running, Failed, Total (0 formatted as "0")
		});

		expect(screen.getByText("0.0%")).toBeInTheDocument();
	});
});

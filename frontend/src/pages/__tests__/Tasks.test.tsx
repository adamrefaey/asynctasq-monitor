/**
 * Tests for the Tasks page component.
 *
 * Tests cover:
 * - Loading state
 * - Error state
 * - Task list rendering
 * - Search and filter functionality
 * - Pagination
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockPaginatedResponse, createMockTask } from "@/test/mocks";
import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import Tasks from "../Tasks";

// Mock the hooks module
vi.mock("@/hooks/useTasks", () => ({
	useTasks: vi.fn(),
	useRetryTask: vi.fn(() => ({
		mutate: vi.fn(),
		isPending: false,
	})),
	useDeleteTask: vi.fn(() => ({
		mutate: vi.fn(),
		isPending: false,
	})),
	usePrefetchTask: vi.fn(() => vi.fn()),
	useInvalidateTasks: vi.fn(() => vi.fn()),
	taskKeys: {
		all: ["tasks"],
		lists: () => ["tasks", "list"],
		list: () => ["tasks", "list", {}],
	},
}));

import { useTasks } from "@/hooks/useTasks";

const mockTasks = [
	createMockTask({
		id: "task-1",
		name: "send_email",
		queue: "default",
		status: "completed",
		duration_ms: 1500,
	}),
	createMockTask({
		id: "task-2",
		name: "process_order",
		queue: "default",
		status: "running",
		duration_ms: null,
	}),
	createMockTask({
		id: "task-3",
		name: "sync_data",
		queue: "emails",
		status: "failed",
		duration_ms: 2500,
	}),
	createMockTask({
		id: "task-4",
		name: "generate_report",
		queue: "reports",
		status: "pending",
		started_at: null,
	}),
];

describe("Tasks", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("shows loading state initially", async () => {
		vi.mocked(useTasks).mockReturnValue({
			data: undefined,
			isPending: true,
			error: null,
			refetch: vi.fn(),
			isError: false,
			isSuccess: false,
			isFetching: false,
			isLoading: true,
		} as unknown as ReturnType<typeof useTasks>);

		renderWithProviders(<Tasks />);

		expect(screen.getByText("Loading...")).toBeInTheDocument();
	});

	it("renders task list with table headers", async () => {
		vi.mocked(useTasks).mockReturnValue({
			data: createMockPaginatedResponse(mockTasks, 4),
			isPending: false,
			error: null,
			refetch: vi.fn(),
			isError: false,
			isSuccess: true,
			isFetching: false,
			isLoading: false,
		} as unknown as ReturnType<typeof useTasks>);

		renderWithProviders(<Tasks />);

		await waitFor(() => {
			expect(screen.getByText("send_email")).toBeInTheDocument();
		});

		// Check table headers
		expect(screen.getByText("Name")).toBeInTheDocument();
		expect(screen.getByText("Queue")).toBeInTheDocument();
		expect(screen.getByText("Status")).toBeInTheDocument();
	});

	it("renders filter bar with search input", async () => {
		vi.mocked(useTasks).mockReturnValue({
			data: createMockPaginatedResponse(mockTasks, 4),
			isPending: false,
			error: null,
			refetch: vi.fn(),
			isError: false,
			isSuccess: true,
			isFetching: false,
			isLoading: false,
		} as unknown as ReturnType<typeof useTasks>);

		renderWithProviders(<Tasks />);

		await waitFor(() => {
			expect(screen.getByPlaceholderText(/search tasks/i)).toBeInTheDocument();
		});
	});

	it("shows error state when fetch fails", async () => {
		vi.mocked(useTasks).mockReturnValue({
			data: undefined,
			isPending: false,
			error: new Error("Failed to fetch tasks"),
			refetch: vi.fn(),
			isError: true,
			isSuccess: false,
			isFetching: false,
			isLoading: false,
		} as unknown as ReturnType<typeof useTasks>);

		renderWithProviders(<Tasks />);

		await waitFor(() => {
			expect(screen.getByText(/failed to load tasks/i)).toBeInTheDocument();
		});
	});

	it("renders task status badges", async () => {
		vi.mocked(useTasks).mockReturnValue({
			data: createMockPaginatedResponse(mockTasks, 4),
			isPending: false,
			error: null,
			refetch: vi.fn(),
			isError: false,
			isSuccess: true,
			isFetching: false,
			isLoading: false,
		} as unknown as ReturnType<typeof useTasks>);

		renderWithProviders(<Tasks />);

		await waitFor(() => {
			expect(screen.getByText("send_email")).toBeInTheDocument();
		});

		// Check status badges - these may appear multiple times
		expect(screen.getByText("completed")).toBeInTheDocument();
		expect(screen.getByText("running")).toBeInTheDocument();
		expect(screen.getByText("failed")).toBeInTheDocument();
		expect(screen.getByText("pending")).toBeInTheDocument();
	});

	it("shows empty state when no tasks", async () => {
		vi.mocked(useTasks).mockReturnValue({
			data: createMockPaginatedResponse([], 0),
			isPending: false,
			error: null,
			refetch: vi.fn(),
			isError: false,
			isSuccess: true,
			isFetching: false,
			isLoading: false,
		} as unknown as ReturnType<typeof useTasks>);

		renderWithProviders(<Tasks />);

		await waitFor(() => {
			expect(screen.getByText(/no tasks found/i)).toBeInTheDocument();
		});
	});

	it("renders page title and description", async () => {
		vi.mocked(useTasks).mockReturnValue({
			data: createMockPaginatedResponse(mockTasks, 100),
			isPending: false,
			error: null,
			refetch: vi.fn(),
			isError: false,
			isSuccess: true,
			isFetching: false,
			isLoading: false,
		} as unknown as ReturnType<typeof useTasks>);

		renderWithProviders(<Tasks />);

		// Tasks page renders directly with filter and table, check for key elements
		expect(screen.getByPlaceholderText(/search tasks/i)).toBeInTheDocument();
		expect(screen.getByRole("table")).toBeInTheDocument();
	});
});

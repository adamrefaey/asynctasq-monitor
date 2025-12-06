/**
 * Tests for the TaskDetailModal component.
 *
 * Tests cover:
 * - Loading state
 * - Error state
 * - Task details display
 * - Timing and execution sections
 * - Task actions (retry, delete)
 * - Error information display
 * - Tags display
 * - Accessibility
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockTask } from "@/test/mocks";
import { TaskDetailModal, TaskDetailTrigger } from "../TaskDetailModal";
import { Button } from "../ui/Button";

// Mock the hooks
const mockUseTask = vi.fn();
const mockUseRetryTask = vi.fn();
const mockUseDeleteTask = vi.fn();

vi.mock("@/hooks/useTasks", () => ({
	useTask: (options: { taskId: string }) => mockUseTask(options),
	useRetryTask: () => mockUseRetryTask(),
	useDeleteTask: () => mockUseDeleteTask(),
}));

// Mock clipboard API
Object.assign(navigator, {
	clipboard: {
		writeText: vi.fn().mockResolvedValue(undefined),
	},
});

// Helper to create QueryClient
function createTestQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: { retry: false },
			mutations: { retry: false },
		},
	});
}

// Helper to render with providers
function renderWithProviders(ui: React.ReactElement) {
	const queryClient = createTestQueryClient();
	const user = userEvent.setup();

	return {
		user,
		...render(
			<QueryClientProvider client={queryClient}>
				<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
					{ui}
				</MemoryRouter>
			</QueryClientProvider>,
		),
	};
}

describe("TaskDetailModal", () => {
	const defaultTask = createMockTask({
		id: "task-123",
		name: "test_task",
		status: "completed",
		queue: "default",
		duration_ms: 1500,
		attempt: 1,
		max_retries: 3,
		priority: 1,
		worker_id: "worker-1",
		args: ["arg1", "arg2"],
		kwargs: { key: "value" },
		result: { success: true },
		tags: ["important", "api"],
	});

	beforeEach(() => {
		vi.clearAllMocks();

		// Default mock implementations
		mockUseTask.mockReturnValue({
			data: defaultTask,
			isPending: false,
			error: null,
		});

		mockUseRetryTask.mockReturnValue({
			mutate: vi.fn(),
			isPending: false,
		});

		mockUseDeleteTask.mockReturnValue({
			mutate: vi.fn(),
			isPending: false,
		});
	});

	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders modal when isOpen is true", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});

		it("does not render when isOpen is false", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen={false} onClose={() => {}} />);

			expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
		});

		it("renders modal title", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("heading", { name: /task details/i })).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Loading State Tests
	// ===========================================================================

	describe("loading state", () => {
		it("shows loading spinner when fetching task", () => {
			mockUseTask.mockReturnValue({
				data: null,
				isPending: true,
				error: null,
			});

			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("img", { name: /loading/i })).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Error State Tests
	// ===========================================================================

	describe("error state", () => {
		it("shows error message when task fetch fails", () => {
			mockUseTask.mockReturnValue({
				data: null,
				isPending: false,
				error: new Error("Failed to fetch task"),
			});

			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Failed to load task details")).toBeInTheDocument();
			expect(screen.getByText("Failed to fetch task")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Task Details Display Tests
	// ===========================================================================

	describe("task details display", () => {
		it("displays task name", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("test_task")).toBeInTheDocument();
		});

		it("displays task ID", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("task-123")).toBeInTheDocument();
		});

		it("displays task status badge", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("completed")).toBeInTheDocument();
		});

		it("displays queue name", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("default")).toBeInTheDocument();
		});

		it("displays worker ID", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("worker-1")).toBeInTheDocument();
		});

		it("displays attempt count", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("1 / 3")).toBeInTheDocument();
		});

		it("displays priority", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("1")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Arguments Display Tests
	// ===========================================================================

	describe("arguments display", () => {
		it("displays positional arguments", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Arguments")).toBeInTheDocument();
			expect(screen.getByText("Positional")).toBeInTheDocument();
		});

		it("displays keyword arguments", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Keyword")).toBeInTheDocument();
		});

		it("does not show arguments section when empty", () => {
			mockUseTask.mockReturnValue({
				data: createMockTask({ args: [], kwargs: {} }),
				isPending: false,
				error: null,
			});

			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.queryByText("Arguments")).not.toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Result Display Tests
	// ===========================================================================

	describe("result display", () => {
		it("displays result when present", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Result")).toBeInTheDocument();
		});

		it("does not show result section when null", () => {
			mockUseTask.mockReturnValue({
				data: createMockTask({ result: null }),
				isPending: false,
				error: null,
			});

			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.queryByText("Result")).not.toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Error Display Tests
	// ===========================================================================

	describe("error display", () => {
		it("displays error information for failed tasks", () => {
			mockUseTask.mockReturnValue({
				data: createMockTask({
					status: "failed",
					exception: "ValueError: Invalid input",
					traceback: "Traceback...",
				}),
				isPending: false,
				error: null,
			});

			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Error")).toBeInTheDocument();
			expect(screen.getByText("ValueError: Invalid input")).toBeInTheDocument();
		});

		it("shows traceback in expandable section", () => {
			mockUseTask.mockReturnValue({
				data: createMockTask({
					status: "failed",
					exception: "Error message",
					traceback: "Full traceback here",
				}),
				isPending: false,
				error: null,
			});

			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("View traceback")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Tags Display Tests
	// ===========================================================================

	describe("tags display", () => {
		it("displays task tags", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Tags")).toBeInTheDocument();
			expect(screen.getByText("important")).toBeInTheDocument();
			expect(screen.getByText("api")).toBeInTheDocument();
		});

		it("does not show tags section when empty", () => {
			mockUseTask.mockReturnValue({
				data: createMockTask({ tags: [] }),
				isPending: false,
				error: null,
			});

			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.queryByText("Tags")).not.toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Action Button Tests
	// ===========================================================================

	describe("action buttons", () => {
		it("shows close button", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			// There may be multiple close buttons (X icon and footer Close button)
			const closeButtons = screen.getAllByRole("button", { name: /close/i });
			expect(closeButtons.length).toBeGreaterThanOrEqual(1);
		});

		it("shows delete button", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
		});

		it("shows retry button for failed tasks that can be retried", () => {
			mockUseTask.mockReturnValue({
				data: createMockTask({
					status: "failed",
					attempt: 1,
					max_retries: 3,
				}),
				isPending: false,
				error: null,
			});

			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("button", { name: /retry task/i })).toBeInTheDocument();
		});

		it("does not show retry button for completed tasks", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.queryByRole("button", { name: /retry task/i })).not.toBeInTheDocument();
		});

		it("calls onClose when close button clicked", async () => {
			const handleClose = vi.fn();
			const { user } = renderWithProviders(
				<TaskDetailModal taskId="task-123" isOpen onClose={handleClose} />,
			);

			// Get all close buttons and click the first one
			const closeButtons = screen.getAllByRole("button", { name: /close/i });
			const closeButton = closeButtons[0];
			if (closeButton) {
				await user.click(closeButton);
			}

			expect(handleClose).toHaveBeenCalled();
		});

		it("calls delete mutation when delete button clicked", async () => {
			const mockDeleteMutate = vi.fn();
			mockUseDeleteTask.mockReturnValue({
				mutate: mockDeleteMutate,
				isPending: false,
			});

			const { user } = renderWithProviders(
				<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />,
			);

			const deleteButton = screen.getByRole("button", { name: /delete/i });
			await user.click(deleteButton);

			expect(mockDeleteMutate).toHaveBeenCalledWith({ taskId: "task-123" }, expect.any(Object));
		});

		it("calls retry mutation when retry button clicked", async () => {
			const mockRetryMutate = vi.fn();
			mockUseRetryTask.mockReturnValue({
				mutate: mockRetryMutate,
				isPending: false,
			});

			mockUseTask.mockReturnValue({
				data: createMockTask({
					id: "task-123",
					status: "failed",
					attempt: 1,
					max_retries: 3,
				}),
				isPending: false,
				error: null,
			});

			const { user } = renderWithProviders(
				<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />,
			);

			const retryButton = screen.getByRole("button", { name: /retry task/i });
			await user.click(retryButton);

			expect(mockRetryMutate).toHaveBeenCalledWith({ taskId: "task-123" }, expect.any(Object));
		});

		it("disables buttons while loading", () => {
			mockUseDeleteTask.mockReturnValue({
				mutate: vi.fn(),
				isPending: true,
			});

			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			const deleteButton = screen.getByRole("button", { name: /deleting/i });
			expect(deleteButton).toBeDisabled();
		});
	});

	// ===========================================================================
	// Copy Functionality Tests
	// ===========================================================================

	describe("copy functionality", () => {
		it("copies task ID when copy button clicked", async () => {
			// Mock clipboard using vi.spyOn
			const writeTextMock = vi.fn().mockResolvedValue(undefined);
			vi.spyOn(navigator.clipboard, "writeText").mockImplementation(writeTextMock);

			const { user } = renderWithProviders(
				<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />,
			);

			const copyButton = screen.getByRole("button", { name: /copy task id/i });
			await user.click(copyButton);

			expect(writeTextMock).toHaveBeenCalledWith("task-123");
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("has dialog role", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});

		it("has accessible title", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("heading", { name: /task details/i })).toBeInTheDocument();
		});

		it("timing section has proper heading", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Timing")).toBeInTheDocument();
		});

		it("execution section has proper heading", () => {
			renderWithProviders(<TaskDetailModal taskId="task-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Execution")).toBeInTheDocument();
		});
	});
});

describe("TaskDetailTrigger", () => {
	const mockTask = createMockTask({
		id: "task-456",
		name: "trigger_test_task",
		status: "running",
		queue: "high-priority",
	});

	it("renders children as trigger", () => {
		renderWithProviders(
			<TaskDetailTrigger task={mockTask}>
				<Button>View Details</Button>
			</TaskDetailTrigger>,
		);

		expect(screen.getByRole("button", { name: /view details/i })).toBeInTheDocument();
	});

	it("opens modal when trigger is clicked", async () => {
		const { user } = renderWithProviders(
			<TaskDetailTrigger task={mockTask}>
				<Button>View Details</Button>
			</TaskDetailTrigger>,
		);

		const trigger = screen.getByRole("button", { name: /view details/i });
		await user.click(trigger);

		await waitFor(() => {
			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});
	});

	it("displays task information in modal", async () => {
		const { user } = renderWithProviders(
			<TaskDetailTrigger task={mockTask}>
				<Button>View</Button>
			</TaskDetailTrigger>,
		);

		await user.click(screen.getByRole("button", { name: /view/i }));

		await waitFor(() => {
			expect(screen.getByText("trigger_test_task")).toBeInTheDocument();
			expect(screen.getByText("task-456")).toBeInTheDocument();
		});
	});
});

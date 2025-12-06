/**
 * Tests for the WorkerDetailModal component.
 *
 * Tests cover:
 * - Loading state
 * - Error state
 * - Worker details display
 * - Overview, resources, and performance sections
 * - Worker actions (pause, resume, shutdown, kill)
 * - Current task display
 * - Queues display
 * - Tags display
 * - Accessibility
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { WorkerDetail } from "@/lib/types";
import { createMockWorker } from "@/test/mocks";
import { Button } from "../ui/Button";
import { WorkerDetailModal, WorkerDetailTrigger } from "../WorkerDetailModal";

// Mock the hooks
const mockUseWorkerDetail = vi.fn();
const mockUsePauseWorker = vi.fn();
const mockUseResumeWorker = vi.fn();
const mockUseShutdownWorker = vi.fn();
const mockUseKillWorker = vi.fn();

vi.mock("@/hooks/useWorkers", () => ({
	useWorkerDetail: (options: { workerId: string }) => mockUseWorkerDetail(options),
	usePauseWorker: () => mockUsePauseWorker(),
	useResumeWorker: () => mockUseResumeWorker(),
	useShutdownWorker: () => mockUseShutdownWorker(),
	useKillWorker: () => mockUseKillWorker(),
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

// Create a mock WorkerDetail from base Worker
function createMockWorkerDetail(overrides: Partial<WorkerDetail> = {}): WorkerDetail {
	const baseWorker = createMockWorker();
	return {
		...baseWorker,
		recent_tasks: [],
		hourly_throughput: [],
		...overrides,
	};
}

describe("WorkerDetailModal", () => {
	const defaultWorker = createMockWorkerDetail({
		id: "worker-123",
		name: "test-worker",
		hostname: "localhost",
		pid: 12345,
		status: "active",
		queues: ["default", "high-priority"],
		tasks_processed: 500,
		tasks_failed: 10,
		success_rate: 98,
		tasks_per_hour: 50,
		cpu_usage: 35.5,
		memory_usage: 45.2,
		memory_mb: 512,
		uptime_seconds: 7200,
		version: "1.0.0",
		is_paused: false,
		tags: ["production", "api"],
	});

	beforeEach(() => {
		vi.clearAllMocks();

		// Default mock implementations
		mockUseWorkerDetail.mockReturnValue({
			data: defaultWorker,
			isPending: false,
			error: null,
		});

		mockUsePauseWorker.mockReturnValue({
			mutate: vi.fn(),
			isPending: false,
		});

		mockUseResumeWorker.mockReturnValue({
			mutate: vi.fn(),
			isPending: false,
		});

		mockUseShutdownWorker.mockReturnValue({
			mutate: vi.fn(),
			isPending: false,
		});

		mockUseKillWorker.mockReturnValue({
			mutate: vi.fn(),
			isPending: false,
		});
	});

	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders modal when isOpen is true", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});

		it("does not render when isOpen is false", () => {
			renderWithProviders(
				<WorkerDetailModal workerId="worker-123" isOpen={false} onClose={() => {}} />,
			);

			expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
		});

		it("renders modal title", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("heading", { name: /worker details/i })).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Loading State Tests
	// ===========================================================================

	describe("loading state", () => {
		it("shows loading spinner when fetching worker", () => {
			mockUseWorkerDetail.mockReturnValue({
				data: null,
				isPending: true,
				error: null,
			});

			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("img", { name: /loading/i })).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Error State Tests
	// ===========================================================================

	describe("error state", () => {
		it("shows error message when worker fetch fails", () => {
			mockUseWorkerDetail.mockReturnValue({
				data: null,
				isPending: false,
				error: new Error("Failed to fetch worker"),
			});

			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Failed to load worker details")).toBeInTheDocument();
			expect(screen.getByText("Failed to fetch worker")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Worker Details Display Tests
	// ===========================================================================

	describe("worker details display", () => {
		it("displays worker name", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("test-worker")).toBeInTheDocument();
		});

		it("displays worker ID", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("worker-123")).toBeInTheDocument();
		});

		it("displays worker status badge", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("active")).toBeInTheDocument();
		});

		it("displays hostname", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("localhost")).toBeInTheDocument();
		});

		it("displays process ID", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("12345")).toBeInTheDocument();
		});

		it("displays version", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("1.0.0")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Resources Section Tests
	// ===========================================================================

	describe("resources section", () => {
		it("displays CPU usage", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("35.5%")).toBeInTheDocument();
			expect(screen.getByText("CPU Usage")).toBeInTheDocument();
		});

		it("displays memory usage", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("45.2%")).toBeInTheDocument();
			expect(screen.getByText("Memory Usage")).toBeInTheDocument();
		});

		it("displays memory MB", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("512MB")).toBeInTheDocument();
			expect(screen.getByText("Memory Used")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Performance Section Tests
	// ===========================================================================

	describe("performance section", () => {
		it("displays tasks processed", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("500")).toBeInTheDocument();
			expect(screen.getByText("Processed")).toBeInTheDocument();
		});

		it("displays tasks failed", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("10")).toBeInTheDocument();
			expect(screen.getByText("Failed")).toBeInTheDocument();
		});

		it("displays success rate", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("98.0%")).toBeInTheDocument();
			expect(screen.getByText("Success Rate")).toBeInTheDocument();
		});

		it("displays tasks per hour", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("50.0")).toBeInTheDocument();
			expect(screen.getByText("Tasks/Hour")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Queues Display Tests
	// ===========================================================================

	describe("queues display", () => {
		it("displays subscribed queues", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Subscribed Queues")).toBeInTheDocument();
			expect(screen.getByText("default")).toBeInTheDocument();
			expect(screen.getByText("high-priority")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Tags Display Tests
	// ===========================================================================

	describe("tags display", () => {
		it("displays worker tags", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("production")).toBeInTheDocument();
			expect(screen.getByText("api")).toBeInTheDocument();
		});

		it("does not show tags section when empty", () => {
			mockUseWorkerDetail.mockReturnValue({
				data: createMockWorkerDetail({ tags: [] }),
				isPending: false,
				error: null,
			});

			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			// Tags heading should appear only once for subscribed queues
			const tagsHeadings = screen.queryAllByText("Tags");
			expect(tagsHeadings.length).toBe(0);
		});
	});

	// ===========================================================================
	// Current Task Display Tests
	// ===========================================================================

	describe("current task display", () => {
		it("shows current task when worker is processing", () => {
			mockUseWorkerDetail.mockReturnValue({
				data: createMockWorkerDetail({
					current_task_id: "task-789",
					current_task_name: "process_data",
				}),
				isPending: false,
				error: null,
			});

			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Currently Processing")).toBeInTheDocument();
			expect(screen.getByText("process_data")).toBeInTheDocument();
		});

		it("does not show current task section when not processing", () => {
			mockUseWorkerDetail.mockReturnValue({
				data: createMockWorkerDetail({
					current_task_id: null,
					current_task_name: null,
				}),
				isPending: false,
				error: null,
			});

			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.queryByText("Currently Processing")).not.toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Action Button Tests
	// ===========================================================================

	describe("action buttons", () => {
		it("shows close button", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			// There are multiple close buttons (X icon and footer Close button)
			const closeButtons = screen.getAllByRole("button", { name: /close/i });
			expect(closeButtons.length).toBeGreaterThanOrEqual(1);
		});

		it("shows pause button for active worker", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("button", { name: /pause/i })).toBeInTheDocument();
		});

		it("shows resume button for paused worker", () => {
			mockUseWorkerDetail.mockReturnValue({
				data: createMockWorkerDetail({ is_paused: true }),
				isPending: false,
				error: null,
			});

			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("button", { name: /resume/i })).toBeInTheDocument();
		});

		it("shows shutdown button", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("button", { name: /shutdown/i })).toBeInTheDocument();
		});

		it("shows kill button", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("button", { name: /kill/i })).toBeInTheDocument();
		});

		it("does not show action buttons for offline worker", () => {
			mockUseWorkerDetail.mockReturnValue({
				data: createMockWorkerDetail({ status: "offline" }),
				isPending: false,
				error: null,
			});

			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.queryByRole("button", { name: /pause/i })).not.toBeInTheDocument();
			expect(screen.queryByRole("button", { name: /shutdown/i })).not.toBeInTheDocument();
			expect(screen.queryByRole("button", { name: /kill/i })).not.toBeInTheDocument();
		});

		it("calls onClose when close button clicked", async () => {
			const handleClose = vi.fn();
			const { user } = renderWithProviders(
				<WorkerDetailModal workerId="worker-123" isOpen onClose={handleClose} />,
			);

			// Get the footer Close button (not the X icon button)
			const closeButtons = screen.getAllByRole("button", { name: /close/i });
			// The footer Close button is usually the second one
			const footerCloseButton = closeButtons.find((btn) => btn.textContent === "Close");
			const buttonToClick = footerCloseButton ?? closeButtons[0];
			if (buttonToClick) {
				await user.click(buttonToClick);
			}

			expect(handleClose).toHaveBeenCalled();
		});

		it("calls pause mutation when pause button clicked", async () => {
			const mockPauseMutate = vi.fn();
			mockUsePauseWorker.mockReturnValue({
				mutate: mockPauseMutate,
				isPending: false,
			});

			const { user } = renderWithProviders(
				<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />,
			);

			const pauseButton = screen.getByRole("button", { name: /pause/i });
			await user.click(pauseButton);

			expect(mockPauseMutate).toHaveBeenCalledWith({ workerId: "worker-123" }, expect.any(Object));
		});

		it("calls resume mutation when resume button clicked", async () => {
			const mockResumeMutate = vi.fn();
			mockUseResumeWorker.mockReturnValue({
				mutate: mockResumeMutate,
				isPending: false,
			});

			mockUseWorkerDetail.mockReturnValue({
				data: createMockWorkerDetail({ id: "worker-123", is_paused: true }),
				isPending: false,
				error: null,
			});

			const { user } = renderWithProviders(
				<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />,
			);

			const resumeButton = screen.getByRole("button", { name: /resume/i });
			await user.click(resumeButton);

			expect(mockResumeMutate).toHaveBeenCalledWith({ workerId: "worker-123" }, expect.any(Object));
		});

		it("calls shutdown mutation when shutdown button clicked", async () => {
			const mockShutdownMutate = vi.fn();
			mockUseShutdownWorker.mockReturnValue({
				mutate: mockShutdownMutate,
				isPending: false,
			});

			const { user } = renderWithProviders(
				<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />,
			);

			const shutdownButton = screen.getByRole("button", { name: /shutdown/i });
			await user.click(shutdownButton);

			expect(mockShutdownMutate).toHaveBeenCalledWith(
				{ workerId: "worker-123" },
				expect.any(Object),
			);
		});

		it("calls kill mutation when kill button clicked", async () => {
			const mockKillMutate = vi.fn();
			mockUseKillWorker.mockReturnValue({
				mutate: mockKillMutate,
				isPending: false,
			});

			const { user } = renderWithProviders(
				<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />,
			);

			const killButton = screen.getByRole("button", { name: /kill/i });
			await user.click(killButton);

			expect(mockKillMutate).toHaveBeenCalledWith(
				{ workerId: "worker-123", force: false },
				expect.any(Object),
			);
		});

		it("disables buttons while action is pending", () => {
			mockUsePauseWorker.mockReturnValue({
				mutate: vi.fn(),
				isPending: true,
			});

			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			const pausingButton = screen.getByRole("button", { name: /pausing/i });
			expect(pausingButton).toBeDisabled();
		});
	});

	// ===========================================================================
	// Copy Functionality Tests
	// ===========================================================================

	describe("copy functionality", () => {
		it("copies worker ID when copy button clicked", async () => {
			// Use vi.spyOn on the globally mocked clipboard
			const writeTextMock = vi.fn().mockResolvedValue(undefined);
			vi.spyOn(navigator.clipboard, "writeText").mockImplementation(writeTextMock);

			const { user } = renderWithProviders(
				<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />,
			);

			const copyButton = screen.getByRole("button", {
				name: /copy worker id/i,
			});
			await user.click(copyButton);

			expect(writeTextMock).toHaveBeenCalledWith("worker-123");
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("has dialog role", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});

		it("has accessible title", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByRole("heading", { name: /worker details/i })).toBeInTheDocument();
		});

		it("has section headings", () => {
			renderWithProviders(<WorkerDetailModal workerId="worker-123" isOpen onClose={() => {}} />);

			expect(screen.getByText("Overview")).toBeInTheDocument();
			expect(screen.getByText("Resources")).toBeInTheDocument();
			expect(screen.getByText("Performance")).toBeInTheDocument();
		});
	});
});

describe("WorkerDetailTrigger", () => {
	const mockWorker = createMockWorker({
		id: "worker-456",
		name: "trigger-worker",
		status: "active",
		queues: ["default"],
	});

	it("renders children as trigger", () => {
		const queryClient = createTestQueryClient();

		render(
			<QueryClientProvider client={queryClient}>
				<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
					<WorkerDetailTrigger worker={mockWorker}>
						<Button>View Details</Button>
					</WorkerDetailTrigger>
				</MemoryRouter>
			</QueryClientProvider>,
		);

		expect(screen.getByRole("button", { name: /view details/i })).toBeInTheDocument();
	});

	it("opens modal when trigger is clicked", async () => {
		const queryClient = createTestQueryClient();
		const user = userEvent.setup();

		render(
			<QueryClientProvider client={queryClient}>
				<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
					<WorkerDetailTrigger worker={mockWorker}>
						<Button>View Details</Button>
					</WorkerDetailTrigger>
				</MemoryRouter>
			</QueryClientProvider>,
		);

		const trigger = screen.getByRole("button", { name: /view details/i });
		await user.click(trigger);

		await waitFor(() => {
			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});
	});

	it("displays worker information in modal", async () => {
		const queryClient = createTestQueryClient();
		const user = userEvent.setup();

		render(
			<QueryClientProvider client={queryClient}>
				<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
					<WorkerDetailTrigger worker={mockWorker}>
						<Button>View</Button>
					</WorkerDetailTrigger>
				</MemoryRouter>
			</QueryClientProvider>,
		);

		await user.click(screen.getByRole("button", { name: /view/i }));

		await waitFor(() => {
			expect(screen.getByText("trigger-worker")).toBeInTheDocument();
			expect(screen.getByText("worker-456")).toBeInTheDocument();
		});
	});
});

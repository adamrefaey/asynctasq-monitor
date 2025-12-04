/**
 * Tests for the Workers page component.
 *
 * Tests cover:
 * - Loading state
 * - Error state
 * - Worker list rendering
 * - Worker status badges
 * - Worker stats summary
 * - Filter functionality
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockWorker } from "@/test/mocks";
import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import Workers from "../Workers";

// Mock the hooks module
vi.mock("@/hooks/useWorkers", () => ({
	useWorkers: vi.fn(),
	useWorkerDetail: vi.fn(() => ({
		data: undefined,
		isPending: false,
		error: null,
	})),
	usePauseWorker: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
	useResumeWorker: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
	useShutdownWorker: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
	useKillWorker: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
	usePrefetchWorker: vi.fn(() => vi.fn()),
	useInvalidateWorkers: vi.fn(() => vi.fn()),
	useWorkerLogs: vi.fn(() => ({
		data: undefined,
		isPending: false,
		error: null,
		isFetching: false,
	})),
	workerKeys: {
		all: ["workers"],
		lists: () => ["workers", "list"],
		list: () => ["workers", "list", {}],
		details: () => ["workers", "detail"],
		detail: (id: string) => ["workers", "detail", id],
		logs: () => ["workers", "logs"],
		workerLogs: () => ["workers", "logs", {}],
	},
}));

import { useWorkers } from "@/hooks/useWorkers";

const mockWorkers = [
	createMockWorker({
		id: "worker-1",
		name: "worker-alpha",
		status: "active",
		queues: ["default", "emails"],
		tasks_processed: 150,
		cpu_usage: 45,
		memory_usage: 60,
	}),
	createMockWorker({
		id: "worker-2",
		name: "worker-beta",
		status: "idle",
		queues: ["default"],
		tasks_processed: 80,
		cpu_usage: 5,
		memory_usage: 30,
	}),
	createMockWorker({
		id: "worker-3",
		name: "worker-gamma",
		status: "offline",
		queues: ["reports"],
		tasks_processed: 200,
		is_online: false,
	}),
];

describe("Workers", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("shows loading state with spinner", async () => {
		vi.mocked(useWorkers).mockReturnValue({
			data: undefined,
			isPending: true,
			error: null,
			isError: false,
			isSuccess: false,
			isFetching: false,
			refetch: vi.fn(),
		} as unknown as ReturnType<typeof useWorkers>);

		renderWithProviders(<Workers />);

		// The page shows a spinner during loading (role="img" with aria-label="Loading...")
		expect(screen.getByRole("img", { name: /loading/i })).toBeInTheDocument();
	});

	it("renders worker cards with names", async () => {
		vi.mocked(useWorkers).mockReturnValue({
			data: { items: mockWorkers, total: 3 },
			isPending: false,
			error: null,
			isError: false,
			isSuccess: true,
			isFetching: false,
			refetch: vi.fn(),
		} as unknown as ReturnType<typeof useWorkers>);

		renderWithProviders(<Workers />);

		await waitFor(() => {
			expect(screen.getByText("worker-alpha")).toBeInTheDocument();
		});

		expect(screen.getByText("worker-beta")).toBeInTheDocument();
		expect(screen.getByText("worker-gamma")).toBeInTheDocument();
	});

	it("renders worker status badges", async () => {
		vi.mocked(useWorkers).mockReturnValue({
			data: { items: mockWorkers, total: 3 },
			isPending: false,
			error: null,
			isError: false,
			isSuccess: true,
			isFetching: false,
			refetch: vi.fn(),
		} as unknown as ReturnType<typeof useWorkers>);

		renderWithProviders(<Workers />);

		await waitFor(() => {
			expect(screen.getByText("worker-alpha")).toBeInTheDocument();
		});

		// Check status badges
		expect(screen.getByText("active")).toBeInTheDocument();
		expect(screen.getByText("idle")).toBeInTheDocument();
		expect(screen.getByText("offline")).toBeInTheDocument();
	});

	it("renders worker stats summary", async () => {
		vi.mocked(useWorkers).mockReturnValue({
			data: { items: mockWorkers, total: 3 },
			isPending: false,
			error: null,
			isError: false,
			isSuccess: true,
			isFetching: false,
			refetch: vi.fn(),
		} as unknown as ReturnType<typeof useWorkers>);

		renderWithProviders(<Workers />);

		await waitFor(() => {
			expect(screen.getByText("Total Workers")).toBeInTheDocument();
		});

		// Check stat cards - use getAllByText for labels that appear multiple times
		expect(screen.getByText("3")).toBeInTheDocument();
		// "Active", "Idle", "Offline" appear both in stats and as filter buttons
		const activeElements = screen.getAllByText("Active");
		expect(activeElements.length).toBeGreaterThanOrEqual(1);
		const idleElements = screen.getAllByText("Idle");
		expect(idleElements.length).toBeGreaterThanOrEqual(1);
		const offlineElements = screen.getAllByText("Offline");
		expect(offlineElements.length).toBeGreaterThanOrEqual(1);
	});

	it("shows error state when fetch fails", async () => {
		vi.mocked(useWorkers).mockReturnValue({
			data: undefined,
			isPending: false,
			error: new Error("Failed to fetch workers"),
			isError: true,
			isSuccess: false,
			isFetching: false,
			refetch: vi.fn(),
		} as unknown as ReturnType<typeof useWorkers>);

		renderWithProviders(<Workers />);

		await waitFor(() => {
			expect(screen.getByText(/failed to load workers/i)).toBeInTheDocument();
		});
	});

	it("shows empty state when no workers", async () => {
		vi.mocked(useWorkers).mockReturnValue({
			data: { items: [], total: 0 },
			isPending: false,
			error: null,
			isError: false,
			isSuccess: true,
			isFetching: false,
			refetch: vi.fn(),
		} as unknown as ReturnType<typeof useWorkers>);

		renderWithProviders(<Workers />);

		await waitFor(() => {
			expect(screen.getByText(/no workers found/i)).toBeInTheDocument();
		});
	});

	it("renders search filter input", async () => {
		vi.mocked(useWorkers).mockReturnValue({
			data: { items: mockWorkers, total: 3 },
			isPending: false,
			error: null,
			isError: false,
			isSuccess: true,
			isFetching: false,
			refetch: vi.fn(),
		} as unknown as ReturnType<typeof useWorkers>);

		renderWithProviders(<Workers />);

		await waitFor(() => {
			expect(screen.getByPlaceholderText(/search workers/i)).toBeInTheDocument();
		});
	});

	it("renders page title", async () => {
		vi.mocked(useWorkers).mockReturnValue({
			data: { items: mockWorkers, total: 3 },
			isPending: false,
			error: null,
			isError: false,
			isSuccess: true,
			isFetching: false,
			refetch: vi.fn(),
		} as unknown as ReturnType<typeof useWorkers>);

		renderWithProviders(<Workers />);

		expect(screen.getByText("Workers")).toBeInTheDocument();
		expect(screen.getByText(/monitor and manage/i)).toBeInTheDocument();
	});
});

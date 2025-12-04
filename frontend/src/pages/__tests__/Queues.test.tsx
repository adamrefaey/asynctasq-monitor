/**
 * Tests for the Queues page component.
 *
 * Tests cover:
 * - Loading state
 * - Error state
 * - Queue list rendering
 * - Queue stats summary
 * - Search and filter functionality
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockQueue } from "@/test/mocks";
import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import Queues from "../Queues";

// Mock the API module
vi.mock("@/lib/api", () => ({
	api: {
		getQueues: vi.fn(),
		pauseQueue: vi.fn(),
		resumeQueue: vi.fn(),
		clearQueue: vi.fn(),
	},
}));

import { api } from "@/lib/api";

const mockQueues = [
	createMockQueue({
		name: "default",
		status: "active",
		depth: 100,
		processing: 5,
		failed_total: 2,
		workers_assigned: 3,
	}),
	createMockQueue({
		name: "emails",
		status: "active",
		depth: 50,
		processing: 2,
		failed_total: 0,
		workers_assigned: 2,
	}),
	createMockQueue({
		name: "reports",
		status: "paused",
		depth: 200,
		processing: 0,
		failed_total: 10,
		workers_assigned: 0,
	}),
];

describe("Queues", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("shows loading state with spinner", async () => {
		// Mock a never-resolving promise to keep loading state
		vi.mocked(api.getQueues).mockImplementation(
			() => new Promise(() => {}), // never resolves
		);

		renderWithProviders(<Queues />);

		// Spinner uses role="img" with aria-label="Loading..."
		expect(screen.getByRole("img", { name: /loading/i })).toBeInTheDocument();
	});

	it("renders queue cards with names", async () => {
		vi.mocked(api.getQueues).mockResolvedValue({ items: mockQueues, total: 3 });

		renderWithProviders(<Queues />);

		await waitFor(() => {
			expect(screen.getByText("default")).toBeInTheDocument();
		});

		expect(screen.getByText("emails")).toBeInTheDocument();
		expect(screen.getByText("reports")).toBeInTheDocument();
	});

	it("renders queue status badges", async () => {
		vi.mocked(api.getQueues).mockResolvedValue({ items: mockQueues, total: 3 });

		renderWithProviders(<Queues />);

		await waitFor(() => {
			expect(screen.getByText("default")).toBeInTheDocument();
		});

		// Check status badges - active appears multiple times, paused once
		const activeBadges = screen.getAllByText("active");
		expect(activeBadges.length).toBeGreaterThanOrEqual(1);
		expect(screen.getByText("paused")).toBeInTheDocument();
	});

	it("renders queue stats summary", async () => {
		vi.mocked(api.getQueues).mockResolvedValue({ items: mockQueues, total: 3 });

		renderWithProviders(<Queues />);

		// Wait for the Queues heading first (always present)
		await waitFor(() => {
			expect(screen.getByRole("heading", { name: "Queues" })).toBeInTheDocument();
		});

		// Then wait for data to load and stats grid to appear
		await waitFor(() => {
			// Check for the stats grid - look for "Active" text in stats
			const activeElements = screen.getAllByText("Active");
			expect(activeElements.length).toBeGreaterThanOrEqual(1);
		});
	});

	it("shows error state when fetch fails", async () => {
		vi.mocked(api.getQueues).mockRejectedValue(new Error("Failed to fetch queues"));

		renderWithProviders(<Queues />);

		await waitFor(() => {
			expect(screen.getByText(/failed to load queues/i)).toBeInTheDocument();
		});
	});

	it("shows empty state when no queues", async () => {
		vi.mocked(api.getQueues).mockResolvedValue({ items: [], total: 0 });

		renderWithProviders(<Queues />);

		await waitFor(() => {
			expect(screen.getByText(/no queues found/i)).toBeInTheDocument();
		});
	});

	it("renders search filter input", async () => {
		vi.mocked(api.getQueues).mockResolvedValue({ items: mockQueues, total: 3 });

		renderWithProviders(<Queues />);

		await waitFor(() => {
			expect(screen.getByPlaceholderText(/search queues/i)).toBeInTheDocument();
		});
	});

	it("renders page title and description", async () => {
		vi.mocked(api.getQueues).mockResolvedValue({ items: mockQueues, total: 3 });

		renderWithProviders(<Queues />);

		expect(screen.getByText("Queues")).toBeInTheDocument();
		expect(screen.getByText(/manage your task queues/i)).toBeInTheDocument();
	});
});

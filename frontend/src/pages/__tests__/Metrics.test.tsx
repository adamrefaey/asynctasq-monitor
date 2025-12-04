/**
 * Tests for the Metrics page component.
 *
 * Tests cover:
 * - Loading state
 * - Error state
 * - Time range selector
 * - Chart sections
 * - Duration percentiles
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockMetricsSummary } from "@/test/mocks";
import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import MetricsPage from "../Metrics";

// Mock the API module
vi.mock("@/lib/api", () => ({
	api: {
		getMetricsSummary: vi.fn(),
	},
}));

// Mock recharts to avoid SVG rendering issues in jsdom
vi.mock("recharts", () => ({
	ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
		<div data-testid="responsive-container">{children}</div>
	),
	AreaChart: ({ children }: { children: React.ReactNode }) => (
		<div data-testid="area-chart">{children}</div>
	),
	BarChart: ({ children }: { children: React.ReactNode }) => (
		<div data-testid="bar-chart">{children}</div>
	),
	LineChart: ({ children }: { children: React.ReactNode }) => (
		<div data-testid="line-chart">{children}</div>
	),
	Area: () => null,
	Bar: () => null,
	Line: () => null,
	CartesianGrid: () => null,
	XAxis: () => null,
	YAxis: () => null,
	Tooltip: () => null,
	Legend: () => null,
}));

import { api } from "@/lib/api";

describe("Metrics", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("shows loading state initially", async () => {
		// Mock a never-resolving promise to keep loading state
		vi.mocked(api.getMetricsSummary).mockImplementation(
			() => new Promise(() => {}), // never resolves
		);

		renderWithProviders(<MetricsPage />);

		expect(screen.getByText("Loading metrics...")).toBeInTheDocument();
	});

	it("renders page title and time range selector", async () => {
		vi.mocked(api.getMetricsSummary).mockResolvedValue(createMockMetricsSummary());

		renderWithProviders(<MetricsPage />);

		await waitFor(() => {
			expect(screen.getByText("Metrics & Analytics")).toBeInTheDocument();
		});

		// The time range selector should be present (uses aria-label)
		expect(screen.getByRole("button", { name: /time range/i })).toBeInTheDocument();
	});

	it("renders chart sections", async () => {
		vi.mocked(api.getMetricsSummary).mockResolvedValue(createMockMetricsSummary());

		renderWithProviders(<MetricsPage />);

		await waitFor(() => {
			expect(screen.getByText("Task Throughput")).toBeInTheDocument();
		});

		// Check chart section titles
		expect(screen.getByText("Status Breakdown")).toBeInTheDocument();
		expect(screen.getByText("Queue Depth")).toBeInTheDocument();
	});

	it("renders duration percentiles section", async () => {
		vi.mocked(api.getMetricsSummary).mockResolvedValue(
			createMockMetricsSummary({
				duration: {
					avg_ms: 50,
					p50_ms: 100,
					p95_ms: 600,
					p99_ms: 1000,
				},
			}),
		);

		renderWithProviders(<MetricsPage />);

		await waitFor(() => {
			expect(screen.getByText("Duration Percentiles")).toBeInTheDocument();
		});

		// Check percentile labels - uses "P50 (Median)", "P95", "P99" format
		expect(screen.getByText("P50 (Median)")).toBeInTheDocument();
		expect(screen.getByText("P95")).toBeInTheDocument();
		expect(screen.getByText("P99")).toBeInTheDocument();
	});

	it("shows error state when API call fails", async () => {
		vi.mocked(api.getMetricsSummary).mockRejectedValue(new Error("Network error"));

		renderWithProviders(<MetricsPage />);

		await waitFor(() => {
			expect(screen.getByText("Failed to load metrics")).toBeInTheDocument();
		});
	});

	it("renders charts with mocked components", async () => {
		vi.mocked(api.getMetricsSummary).mockResolvedValue(createMockMetricsSummary());

		renderWithProviders(<MetricsPage />);

		await waitFor(() => {
			expect(screen.getByText("Task Throughput")).toBeInTheDocument();
		});

		// Check for mocked chart containers
		expect(screen.getAllByTestId("responsive-container").length).toBeGreaterThan(0);
	});

	it("handles empty throughput data gracefully", async () => {
		vi.mocked(api.getMetricsSummary).mockResolvedValue(
			createMockMetricsSummary({
				throughput: [],
			}),
		);

		renderWithProviders(<MetricsPage />);

		await waitFor(() => {
			expect(screen.getByText("Task Throughput")).toBeInTheDocument();
		});
	});

	it("handles missing queue depth data", async () => {
		vi.mocked(api.getMetricsSummary).mockResolvedValue(
			createMockMetricsSummary({
				queue_depth: [],
			}),
		);

		renderWithProviders(<MetricsPage />);

		await waitFor(() => {
			expect(screen.getByText("Queue Depth")).toBeInTheDocument();
		});
	});
});

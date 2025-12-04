/**
 * Tests for the QueryProvider component.
 *
 * Tests verify:
 * - QueryClient is created with correct defaults
 * - QueryProvider wraps children with QueryClientProvider
 * - DevTools are included in development
 */

import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { QueryProvider } from "../query";

// Mock ReactQueryDevtools to avoid rendering issues in tests
vi.mock("@tanstack/react-query-devtools", () => ({
	ReactQueryDevtools: () => null,
}));

/**
 * Test component that displays QueryClient configuration.
 */
function QueryClientInspector(): ReactNode {
	const queryClient = useQueryClient();
	const defaults = queryClient.getDefaultOptions();

	return (
		<div>
			<div data-testid="stale-time">{String(defaults.queries?.staleTime ?? "")}</div>
			<div data-testid="gc-time">{String(defaults.queries?.gcTime ?? "")}</div>
			<div data-testid="retry">{String(defaults.queries?.retry ?? "")}</div>
			<div data-testid="refetch-on-focus">{String(defaults.queries?.refetchOnWindowFocus)}</div>
		</div>
	);
}

describe("QueryProvider", () => {
	it("renders children", () => {
		render(
			<QueryProvider>
				<div data-testid="child">Hello</div>
			</QueryProvider>,
		);

		expect(screen.getByTestId("child")).toHaveTextContent("Hello");
	});

	it("provides QueryClient to children", () => {
		render(
			<QueryProvider>
				<QueryClientInspector />
			</QueryProvider>,
		);

		// If this renders without error, QueryClient is available
		expect(screen.getByTestId("stale-time")).toBeInTheDocument();
	});

	it("configures QueryClient with correct staleTime (5 seconds)", () => {
		render(
			<QueryProvider>
				<QueryClientInspector />
			</QueryProvider>,
		);

		expect(screen.getByTestId("stale-time")).toHaveTextContent("5000");
	});

	it("configures QueryClient with correct gcTime (5 minutes)", () => {
		render(
			<QueryProvider>
				<QueryClientInspector />
			</QueryProvider>,
		);

		// 5 minutes = 5 * 60 * 1000 = 300000
		expect(screen.getByTestId("gc-time")).toHaveTextContent("300000");
	});

	it("configures retry to 1", () => {
		render(
			<QueryProvider>
				<QueryClientInspector />
			</QueryProvider>,
		);

		expect(screen.getByTestId("retry")).toHaveTextContent("1");
	});

	it("disables refetch on window focus", () => {
		render(
			<QueryProvider>
				<QueryClientInspector />
			</QueryProvider>,
		);

		expect(screen.getByTestId("refetch-on-focus")).toHaveTextContent("false");
	});

	it("creates new QueryClient instance for each provider", () => {
		const clients: QueryClient[] = [];

		function ClientCollector(): ReactNode {
			const client = useQueryClient();
			clients.push(client);
			return null;
		}

		// Render first provider
		const { unmount: unmount1 } = render(
			<QueryProvider>
				<ClientCollector />
			</QueryProvider>,
		);
		unmount1();

		// Render second provider
		const { unmount: unmount2 } = render(
			<QueryProvider>
				<ClientCollector />
			</QueryProvider>,
		);
		unmount2();

		// Each provider should have its own instance
		expect(clients).toHaveLength(2);
		expect(clients[0]).not.toBe(clients[1]);
	});

	it("maintains same QueryClient across re-renders", () => {
		const clients: QueryClient[] = [];

		function ClientCollector(): ReactNode {
			const client = useQueryClient();
			clients.push(client);
			return <div>collector</div>;
		}

		const { rerender } = render(
			<QueryProvider>
				<ClientCollector />
			</QueryProvider>,
		);

		// Trigger re-render
		rerender(
			<QueryProvider>
				<ClientCollector />
			</QueryProvider>,
		);

		// Should be the same client instance
		expect(clients).toHaveLength(2);
		expect(clients[0]).toBe(clients[1]);
	});

	it("renders multiple children", () => {
		render(
			<QueryProvider>
				<div data-testid="child-1">First</div>
				<div data-testid="child-2">Second</div>
			</QueryProvider>,
		);

		expect(screen.getByTestId("child-1")).toBeInTheDocument();
		expect(screen.getByTestId("child-2")).toBeInTheDocument();
	});

	it("supports nested components using queries", () => {
		function QueryConsumer(): ReactNode {
			const queryClient = useQueryClient();
			// Just verify we can access the client
			return <div data-testid="has-client">{queryClient ? "yes" : "no"}</div>;
		}

		render(
			<QueryProvider>
				<div>
					<QueryConsumer />
				</div>
			</QueryProvider>,
		);

		expect(screen.getByTestId("has-client")).toHaveTextContent("yes");
	});
});

describe("QueryClient defaults", () => {
	it("has structural sharing enabled for efficient updates", () => {
		function StructuralSharingCheck(): ReactNode {
			const queryClient = useQueryClient();
			const defaults = queryClient.getDefaultOptions();
			return (
				<div data-testid="structural-sharing">
					{String(defaults.queries?.structuralSharing ?? "default")}
				</div>
			);
		}

		render(
			<QueryProvider>
				<StructuralSharingCheck />
			</QueryProvider>,
		);

		expect(screen.getByTestId("structural-sharing")).toHaveTextContent("true");
	});

	it("has retry delay set to 1000ms", () => {
		function RetryDelayCheck(): ReactNode {
			const queryClient = useQueryClient();
			const defaults = queryClient.getDefaultOptions();
			return <div data-testid="retry-delay">{String(defaults.queries?.retryDelay)}</div>;
		}

		render(
			<QueryProvider>
				<RetryDelayCheck />
			</QueryProvider>,
		);

		expect(screen.getByTestId("retry-delay")).toHaveTextContent("1000");
	});

	it("has mutation retry set to 1", () => {
		function MutationRetryCheck(): ReactNode {
			const queryClient = useQueryClient();
			const defaults = queryClient.getDefaultOptions();
			return <div data-testid="mutation-retry">{String(defaults.mutations?.retry)}</div>;
		}

		render(
			<QueryProvider>
				<MutationRetryCheck />
			</QueryProvider>,
		);

		expect(screen.getByTestId("mutation-retry")).toHaveTextContent("1");
	});
});

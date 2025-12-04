/**
 * Tests for the RootLayout component.
 *
 * Tests cover:
 * - Basic rendering
 * - Sidebar integration
 * - Header integration
 * - WebSocket connection status
 * - Keyboard shortcuts
 * - Key sequence indicator
 * - Outlet rendering
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RootLayout } from "../RootLayout";

// Mock hooks
const mockUseWebSocket = vi.fn();
const mockUseKeyboardShortcuts = vi.fn();

vi.mock("@/hooks/useWebSocket", () => ({
	useWebSocket: (options: { room: string; autoConnect: boolean }) => mockUseWebSocket(options),
}));

vi.mock("@/hooks/useKeyboardShortcuts", () => ({
	useKeyboardShortcuts: (options?: { enabled?: boolean; onShowHelp?: () => void }) =>
		mockUseKeyboardShortcuts(options),
}));

vi.mock("@/hooks/useTheme", () => ({
	useTheme: () => ({
		theme: "light",
		toggleTheme: vi.fn(),
	}),
}));

// Helper to create QueryClient
function createTestQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: { retry: false },
			mutations: { retry: false },
		},
	});
}

// Helper to render RootLayout with all providers
function renderRootLayout(initialPath = "/") {
	const queryClient = createTestQueryClient();

	return render(
		<QueryClientProvider client={queryClient}>
			<MemoryRouter initialEntries={[initialPath]}>
				<Routes>
					<Route element={<RootLayout />}>
						<Route path="/" element={<div>Dashboard Page</div>} />
						<Route path="/tasks" element={<div>Tasks Page</div>} />
					</Route>
				</Routes>
			</MemoryRouter>
		</QueryClientProvider>,
	);
}

describe("RootLayout", () => {
	beforeEach(() => {
		vi.clearAllMocks();

		// Default mock implementations
		mockUseWebSocket.mockReturnValue({
			isConnected: false,
		});

		mockUseKeyboardShortcuts.mockReturnValue({
			shortcutsByCategory: {
				navigation: [],
				actions: [],
				general: [],
				modal: [],
			},
			currentSequence: "",
		});
	});

	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders sidebar", () => {
			renderRootLayout();

			expect(screen.getByRole("complementary")).toBeInTheDocument();
		});

		it("renders header", () => {
			renderRootLayout();

			expect(screen.getByRole("banner")).toBeInTheDocument();
		});

		it("renders main content area", () => {
			renderRootLayout();

			expect(screen.getByRole("main")).toBeInTheDocument();
		});

		it("renders child routes via Outlet", () => {
			renderRootLayout("/");

			expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
		});

		it("renders different pages based on route", () => {
			renderRootLayout("/tasks");

			expect(screen.getByText("Tasks Page")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// WebSocket Integration Tests
	// ===========================================================================

	describe("WebSocket integration", () => {
		it("initializes WebSocket with global room", () => {
			renderRootLayout();

			expect(mockUseWebSocket).toHaveBeenCalledWith({
				room: "global",
				autoConnect: true,
			});
		});

		it("passes connection status to Header", () => {
			mockUseWebSocket.mockReturnValue({ isConnected: true });
			renderRootLayout();

			expect(screen.getByText("Live")).toBeInTheDocument();
		});

		it("shows Offline when disconnected", () => {
			mockUseWebSocket.mockReturnValue({ isConnected: false });
			renderRootLayout();

			expect(screen.getByText("Offline")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Keyboard Shortcuts Integration Tests
	// ===========================================================================

	describe("keyboard shortcuts integration", () => {
		it("initializes keyboard shortcuts", () => {
			renderRootLayout();

			expect(mockUseKeyboardShortcuts).toHaveBeenCalledWith(
				expect.objectContaining({
					enabled: true,
					onShowHelp: expect.any(Function),
				}),
			);
		});

		it("does not show key sequence indicator when no sequence", () => {
			mockUseKeyboardShortcuts.mockReturnValue({
				shortcutsByCategory: {
					navigation: [],
					actions: [],
					general: [],
					modal: [],
				},
				currentSequence: "",
			});
			renderRootLayout();

			expect(screen.queryByText("Keys:")).not.toBeInTheDocument();
		});

		it("shows key sequence indicator when there is a sequence", () => {
			mockUseKeyboardShortcuts.mockReturnValue({
				shortcutsByCategory: {
					navigation: [],
					actions: [],
					general: [],
					modal: [],
				},
				currentSequence: "g",
			});
			renderRootLayout();

			expect(screen.getByText("Keys:")).toBeInTheDocument();
			expect(screen.getByText("g")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Layout Structure Tests
	// ===========================================================================

	describe("layout structure", () => {
		it("has sidebar on the left", () => {
			renderRootLayout();

			const sidebar = screen.getByRole("complementary");
			expect(sidebar).toHaveClass("fixed", "left-0");
		});

		it("has main content with left padding for sidebar", () => {
			renderRootLayout();

			// Find the div that contains the Header and main
			const mainContainer = screen.getByRole("main").parentElement;
			expect(mainContainer).toHaveClass("pl-64");
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("has proper landmark roles", () => {
			renderRootLayout();

			expect(screen.getByRole("complementary")).toBeInTheDocument(); // sidebar
			expect(screen.getByRole("banner")).toBeInTheDocument(); // header
			expect(screen.getByRole("main")).toBeInTheDocument(); // main content
		});

		it("navigation is in sidebar", () => {
			renderRootLayout();

			const sidebar = screen.getByRole("complementary");
			const nav = screen.getByRole("navigation");

			expect(sidebar).toContainElement(nav);
		});
	});
});

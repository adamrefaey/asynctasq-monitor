/**
 * Tests for the Header component.
 *
 * Tests cover:
 * - Basic rendering
 * - Page title display based on route
 * - Connection status indicator
 * - Theme toggle functionality
 * - Search input
 * - Accessibility
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test/test-utils";
import { Header } from "../Header";

// Mock useTheme hook
const mockToggleTheme = vi.fn();
vi.mock("@/hooks/useTheme", () => ({
	useTheme: () => ({
		theme: "light",
		toggleTheme: mockToggleTheme,
	}),
}));

// Mock useLocation from react-router-dom
vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useLocation: () => ({ pathname: "/" }),
	};
});

describe("Header", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders header element", () => {
			renderWithProviders(<Header />);

			expect(screen.getByRole("banner")).toBeInTheDocument();
		});

		it("renders page title", () => {
			renderWithProviders(<Header />);

			expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
		});

		it("renders search input", () => {
			renderWithProviders(<Header />);

			expect(screen.getByRole("searchbox")).toBeInTheDocument();
		});

		it("renders theme toggle button", () => {
			renderWithProviders(<Header />);

			expect(screen.getByRole("button", { name: /switch to dark mode/i })).toBeInTheDocument();
		});

		it("renders notifications button", () => {
			renderWithProviders(<Header />);

			expect(screen.getByRole("button", { name: /notifications/i })).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Page Title Tests
	// ===========================================================================

	describe("page title", () => {
		it("displays Dashboard title for root path", () => {
			renderWithProviders(<Header />);

			expect(screen.getByRole("heading", { name: /dashboard/i })).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Connection Status Tests
	// ===========================================================================

	describe("connection status", () => {
		it("shows connected status when isConnected is true", () => {
			renderWithProviders(<Header isConnected />);

			expect(screen.getByText("Live")).toBeInTheDocument();
		});

		it("shows disconnected status when isConnected is false", () => {
			renderWithProviders(<Header isConnected={false} />);

			expect(screen.getByText("Offline")).toBeInTheDocument();
		});

		it("shows disconnected by default", () => {
			renderWithProviders(<Header />);

			expect(screen.getByText("Offline")).toBeInTheDocument();
		});

		it("has accessible title for connection status", () => {
			renderWithProviders(<Header isConnected />);

			expect(screen.getByTitle("Connected")).toBeInTheDocument();
		});

		it("has accessible title for disconnected status", () => {
			renderWithProviders(<Header isConnected={false} />);

			expect(screen.getByTitle("Disconnected")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Theme Toggle Tests
	// ===========================================================================

	describe("theme toggle", () => {
		it("calls toggleTheme when clicked", async () => {
			const { user } = renderWithProviders(<Header />);

			const themeButton = screen.getByRole("button", { name: /switch to dark mode/i });
			await user.click(themeButton);

			expect(mockToggleTheme).toHaveBeenCalledTimes(1);
		});
	});

	// ===========================================================================
	// Search Input Tests
	// ===========================================================================

	describe("search input", () => {
		it("has placeholder text", () => {
			renderWithProviders(<Header />);

			expect(screen.getByPlaceholderText("Search tasks...")).toBeInTheDocument();
		});

		it("allows typing in search input", async () => {
			const { user } = renderWithProviders(<Header />);

			const searchInput = screen.getByRole("searchbox");
			await user.type(searchInput, "test query");

			expect(searchInput).toHaveValue("test query");
		});

		it("can be cleared", async () => {
			const { user } = renderWithProviders(<Header />);

			const searchInput = screen.getByRole("searchbox");
			await user.type(searchInput, "test");
			await user.clear(searchInput);

			expect(searchInput).toHaveValue("");
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("header has banner role", () => {
			renderWithProviders(<Header />);

			expect(screen.getByRole("banner")).toBeInTheDocument();
		});

		it("page title is heading level 1", () => {
			renderWithProviders(<Header />);

			const heading = screen.getByRole("heading", { level: 1 });
			expect(heading).toBeInTheDocument();
		});

		it("theme toggle has descriptive aria-label", () => {
			renderWithProviders(<Header />);

			expect(screen.getByRole("button", { name: /switch to dark mode/i })).toBeInTheDocument();
		});

		it("notifications button has aria-label", () => {
			renderWithProviders(<Header />);

			expect(screen.getByRole("button", { name: /notifications/i })).toBeInTheDocument();
		});
	});
});

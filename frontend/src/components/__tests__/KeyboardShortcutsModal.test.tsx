/**
 * Tests for the KeyboardShortcutsModal component.
 *
 * Tests cover:
 * - Basic rendering
 * - Opening and closing behavior
 * - Shortcut categories display
 * - Key sequence rendering
 * - Accessibility
 */

import { describe, expect, it, vi } from "vitest";
import type { ShortcutsByCategory } from "@/hooks/useKeyboardShortcuts";
import { renderWithProviders, screen } from "@/test/test-utils";
import { KeyboardShortcutsModal } from "../KeyboardShortcutsModal";

const mockShortcuts: ShortcutsByCategory = {
	navigation: [
		{
			keys: "g d",
			description: "Go to Dashboard",
			handler: vi.fn(),
			category: "navigation",
		},
		{
			keys: "g t",
			description: "Go to Tasks",
			handler: vi.fn(),
			category: "navigation",
		},
	],
	actions: [
		{
			keys: "r",
			description: "Refresh data",
			handler: vi.fn(),
			category: "actions",
		},
		{
			keys: "n",
			description: "New task",
			handler: vi.fn(),
			category: "actions",
		},
	],
	general: [
		{
			keys: "?",
			description: "Show help",
			handler: vi.fn(),
			category: "general",
		},
		{
			keys: "/",
			description: "Focus search",
			handler: vi.fn(),
			category: "general",
		},
	],
	modal: [
		{
			keys: "Escape",
			description: "Close modal",
			handler: vi.fn(),
			category: "modal",
		},
	],
};

describe("KeyboardShortcutsModal", () => {
	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders when isOpen is true", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});

		it("does not render when isOpen is false", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen={false} onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
		});

		it("renders modal title", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.getByRole("heading", { name: /keyboard shortcuts/i })).toBeInTheDocument();
		});

		it("renders close button", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			// There may be multiple elements with close - use getAllByRole
			const closeButtons = screen.getAllByRole("button", { name: /close/i });
			expect(closeButtons.length).toBeGreaterThanOrEqual(1);
		});
	});

	// ===========================================================================
	// Category Display Tests
	// ===========================================================================

	describe("shortcut categories", () => {
		it("renders Navigation category", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.getByRole("heading", { name: "Navigation" })).toBeInTheDocument();
		});

		it("renders Actions category", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.getByRole("heading", { name: "Actions" })).toBeInTheDocument();
		});

		it("renders General category", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.getByRole("heading", { name: "General" })).toBeInTheDocument();
		});

		it("renders Modal category when it has shortcuts", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.getByRole("heading", { name: "Modal" })).toBeInTheDocument();
		});

		it("does not render Modal category when empty", () => {
			const shortcutsWithoutModal = {
				...mockShortcuts,
				modal: [],
			};

			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={shortcutsWithoutModal} />,
			);

			expect(screen.queryByRole("heading", { name: "Modal" })).not.toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Shortcut Display Tests
	// ===========================================================================

	describe("shortcut display", () => {
		it("displays shortcut descriptions", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.getByText("Go to Dashboard")).toBeInTheDocument();
			expect(screen.getByText("Go to Tasks")).toBeInTheDocument();
			expect(screen.getByText("Refresh data")).toBeInTheDocument();
		});

		it("displays key sequences with kbd elements", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			// Check for kbd elements
			const kbds = document.querySelectorAll("kbd");
			expect(kbds.length).toBeGreaterThan(0);
		});

		it("shows 'then' between key sequence parts", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			// For "g d" sequence, there should be "then" between g and d
			expect(screen.getAllByText("then").length).toBeGreaterThan(0);
		});
	});

	// ===========================================================================
	// Close Behavior Tests
	// ===========================================================================

	describe("close behavior", () => {
		it("calls onClose when close button is clicked", async () => {
			const handleClose = vi.fn();
			const { user } = renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={handleClose} shortcuts={mockShortcuts} />,
			);

			// Multiple close buttons may exist - get the X icon button (aria-label="Close dialog")
			const closeButtons = screen.getAllByRole("button", { name: /close/i });
			const closeButton = closeButtons[0];
			if (closeButton) {
				await user.click(closeButton);
			}

			expect(handleClose).toHaveBeenCalledTimes(1);
		});

		it("calls onClose when Escape key is pressed", async () => {
			const handleClose = vi.fn();
			const { user } = renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={handleClose} shortcuts={mockShortcuts} />,
			);

			await user.keyboard("{Escape}");

			expect(handleClose).toHaveBeenCalled();
		});
	});

	// ===========================================================================
	// Hint Text Tests
	// ===========================================================================

	describe("hint text", () => {
		it("displays hint about showing shortcuts", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.getByText(/press/i)).toBeInTheDocument();
			// "?" appears multiple times as a key indicator in shortcuts - use getAllByText
			const questionMarks = screen.getAllByText("?");
			expect(questionMarks.length).toBeGreaterThanOrEqual(1);
			expect(screen.getByText(/anytime to show this help/i)).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("has dialog role", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});

		it("has accessible title", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			expect(screen.getByRole("heading", { name: /keyboard shortcuts/i })).toBeInTheDocument();
		});

		it("category headings have proper hierarchy", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			// Main title is in a heading, categories are h3
			const categoryHeadings = screen.getAllByRole("heading", { level: 3 });
			expect(categoryHeadings.length).toBeGreaterThanOrEqual(3);
		});

		it("kbd elements are used for key representation", () => {
			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={mockShortcuts} />,
			);

			const kbdElements = document.querySelectorAll("kbd");
			expect(kbdElements.length).toBeGreaterThan(0);
		});
	});

	// ===========================================================================
	// Empty State Tests
	// ===========================================================================

	describe("empty states", () => {
		it("handles empty navigation shortcuts", () => {
			const emptyShortcuts: ShortcutsByCategory = {
				navigation: [],
				actions: mockShortcuts.actions,
				general: mockShortcuts.general,
				modal: [],
			};

			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={emptyShortcuts} />,
			);

			// Navigation section should not render if empty
			expect(screen.queryByRole("heading", { name: "Navigation" })).not.toBeInTheDocument();
		});

		it("handles all empty shortcuts", () => {
			const emptyShortcuts: ShortcutsByCategory = {
				navigation: [],
				actions: [],
				general: [],
				modal: [],
			};

			renderWithProviders(
				<KeyboardShortcutsModal isOpen onClose={() => {}} shortcuts={emptyShortcuts} />,
			);

			// Modal should still render with hint text
			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});
	});
});

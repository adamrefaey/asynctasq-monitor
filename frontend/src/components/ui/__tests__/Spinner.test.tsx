/**
 * Tests for the Spinner component.
 *
 * Tests cover:
 * - Basic rendering
 * - Size variants
 * - Color variants
 * - Custom className
 * - Accessibility (aria-label, role)
 * - LoadingOverlay component
 */

import { describe, expect, it } from "vitest";
import { render, screen } from "@/test/test-utils";
import { LoadingOverlay, Spinner } from "../Spinner";

describe("Spinner", () => {
	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders as an SVG element", () => {
			render(<Spinner />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner.tagName.toLowerCase()).toBe("svg");
		});

		it("has default aria-label of Loading...", () => {
			render(<Spinner />);

			expect(screen.getByRole("img", { name: /loading/i })).toBeInTheDocument();
		});

		it("applies custom className", () => {
			render(<Spinner className="custom-class" />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("custom-class");
		});

		it("has animation class", () => {
			render(<Spinner />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("animate-spin");
		});
	});

	// ===========================================================================
	// Size Tests
	// ===========================================================================

	describe("sizes", () => {
		it("renders sm size", () => {
			render(<Spinner size="sm" />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("h-4");
			expect(spinner).toHaveClass("w-4");
		});

		it("renders md size (default)", () => {
			render(<Spinner size="md" />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("h-6");
			expect(spinner).toHaveClass("w-6");
		});

		it("renders lg size", () => {
			render(<Spinner size="lg" />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("h-8");
			expect(spinner).toHaveClass("w-8");
		});

		it("renders xl size", () => {
			render(<Spinner size="xl" />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("h-12");
			expect(spinner).toHaveClass("w-12");
		});
	});

	// ===========================================================================
	// Color Tests
	// ===========================================================================

	describe("colors", () => {
		it("renders default color", () => {
			render(<Spinner color="default" />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("text-zinc-400");
		});

		it("renders primary color", () => {
			render(<Spinner color="primary" />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("text-blue-600");
		});

		it("renders white color", () => {
			render(<Spinner color="white" />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("text-white");
		});

		it("renders current color", () => {
			render(<Spinner color="current" />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("text-current");
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("has role of img", () => {
			render(<Spinner />);

			expect(screen.getByRole("img")).toBeInTheDocument();
		});

		it("supports custom label", () => {
			render(<Spinner label="Processing..." />);

			expect(screen.getByRole("img", { name: /processing/i })).toBeInTheDocument();
		});

		it("has title element for accessibility", () => {
			render(<Spinner label="Custom Loading" />);

			expect(screen.getByTitle("Custom Loading")).toBeInTheDocument();
		});
	});
});

describe("LoadingOverlay", () => {
	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders with default label", () => {
			render(<LoadingOverlay />);

			// The text "Loading..." appears twice - in the SVG title and as a paragraph
			// Use getAllByText to handle multiple matches
			const loadingElements = screen.getAllByText("Loading...");
			expect(loadingElements.length).toBeGreaterThanOrEqual(1);
		});

		it("renders spinner", () => {
			render(<LoadingOverlay />);

			expect(screen.getByRole("img", { name: /loading/i })).toBeInTheDocument();
		});

		it("renders custom children instead of default label", () => {
			render(<LoadingOverlay>Custom loading message</LoadingOverlay>);

			expect(screen.getByText("Custom loading message")).toBeInTheDocument();
		});

		it("renders spinner with lg size", () => {
			render(<LoadingOverlay />);

			const spinner = screen.getByRole("img", { name: /loading/i });
			expect(spinner).toHaveClass("h-8");
			expect(spinner).toHaveClass("w-8");
		});
	});

	// ===========================================================================
	// Label Tests
	// ===========================================================================

	describe("labels", () => {
		it("supports custom label prop", () => {
			render(<LoadingOverlay label="Fetching data..." />);

			expect(screen.getByText("Fetching data...")).toBeInTheDocument();
		});

		it("prefers children over label prop", () => {
			render(
				<LoadingOverlay label="Label text">
					<span>Children text</span>
				</LoadingOverlay>,
			);

			expect(screen.getByText("Children text")).toBeInTheDocument();
			expect(screen.queryByText("Label text")).not.toBeInTheDocument();
		});
	});
});

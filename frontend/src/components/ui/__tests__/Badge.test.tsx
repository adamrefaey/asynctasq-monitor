/**
 * Tests for the Badge component.
 *
 * Tests cover:
 * - Rendering with different variants
 * - Rendering with different sizes
 * - Dot indicator display
 * - Custom className support
 * - Helper functions for status badge variants
 * - Accessibility
 */

import { describe, expect, it } from "vitest";
import { render, screen } from "@/test/test-utils";
import { Badge, getTaskStatusBadgeVariant, getWorkerStatusBadgeVariant } from "../Badge";

describe("Badge", () => {
	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders children correctly", () => {
			render(<Badge>Test Badge</Badge>);

			expect(screen.getByText("Test Badge")).toBeInTheDocument();
		});

		it("renders with default variant and size", () => {
			render(<Badge>Default</Badge>);

			const badge = screen.getByText("Default");
			expect(badge).toBeInTheDocument();
			expect(badge.tagName.toLowerCase()).toBe("span");
		});

		it("applies custom className", () => {
			render(<Badge className="custom-class">Custom</Badge>);

			const badge = screen.getByText("Custom");
			expect(badge).toHaveClass("custom-class");
		});
	});

	// ===========================================================================
	// Variant Tests
	// ===========================================================================

	describe("variants", () => {
		it.each([
			"default",
			"success",
			"warning",
			"error",
			"info",
			"pending",
			"running",
		] as const)("renders %s variant", (variant) => {
			render(<Badge variant={variant}>{variant} badge</Badge>);

			expect(screen.getByText(`${variant} badge`)).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Size Tests
	// ===========================================================================

	describe("sizes", () => {
		it.each(["sm", "md", "lg"] as const)("renders %s size", (size) => {
			render(<Badge size={size}>{size} badge</Badge>);

			expect(screen.getByText(`${size} badge`)).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Dot Indicator Tests
	// ===========================================================================

	describe("dot indicator", () => {
		it("does not render dot by default", () => {
			render(<Badge>No Dot</Badge>);

			const badge = screen.getByText("No Dot");
			// Badge should only contain the text, no dot
			expect(badge.childElementCount).toBe(0);
		});

		it("renders dot when dot prop is true", () => {
			render(<Badge dot>With Dot</Badge>);

			const badge = screen.getByText("With Dot");
			// Badge should have a child element for the dot
			expect(badge.querySelector("span")).toBeInTheDocument();
		});

		it("dot has aria-hidden for accessibility", () => {
			render(<Badge dot>With Dot</Badge>);

			const badge = screen.getByText("With Dot");
			const dot = badge.querySelector("span");
			expect(dot).toHaveAttribute("aria-hidden", "true");
		});
	});

	// ===========================================================================
	// Helper Function Tests
	// ===========================================================================

	describe("getTaskStatusBadgeVariant", () => {
		it("returns pending variant for pending status", () => {
			expect(getTaskStatusBadgeVariant("pending")).toBe("pending");
		});

		it("returns running variant for running status", () => {
			expect(getTaskStatusBadgeVariant("running")).toBe("running");
		});

		it("returns success variant for completed status", () => {
			expect(getTaskStatusBadgeVariant("completed")).toBe("success");
		});

		it("returns error variant for failed status", () => {
			expect(getTaskStatusBadgeVariant("failed")).toBe("error");
		});

		it("returns warning variant for retrying status", () => {
			expect(getTaskStatusBadgeVariant("retrying")).toBe("warning");
		});

		it("returns default variant for cancelled status", () => {
			expect(getTaskStatusBadgeVariant("cancelled")).toBe("default");
		});

		it("returns default variant for unknown status", () => {
			expect(getTaskStatusBadgeVariant("unknown")).toBe("default");
		});
	});

	describe("getWorkerStatusBadgeVariant", () => {
		it("returns success variant for active status", () => {
			expect(getWorkerStatusBadgeVariant("active")).toBe("success");
		});

		it("returns info variant for idle status", () => {
			expect(getWorkerStatusBadgeVariant("idle")).toBe("info");
		});

		it("returns error variant for down status", () => {
			expect(getWorkerStatusBadgeVariant("down")).toBe("error");
		});

		it("returns default variant for unknown status", () => {
			expect(getWorkerStatusBadgeVariant("unknown")).toBe("default");
		});
	});
});

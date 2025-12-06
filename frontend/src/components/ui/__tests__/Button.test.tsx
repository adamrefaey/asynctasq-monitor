/**
 * Tests for the Button component.
 *
 * Tests cover:
 * - Rendering with different variants
 * - Rendering with different sizes
 * - Click handling (onPress)
 * - Disabled state
 * - Custom className support
 * - Accessibility (focus, aria attributes)
 */

import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test/test-utils";
import { Button } from "../Button";

describe("Button", () => {
	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders children correctly", () => {
			renderWithProviders(<Button>Click me</Button>);

			expect(screen.getByRole("button", { name: /click me/i })).toBeInTheDocument();
		});

		it("renders with default variant and size", () => {
			renderWithProviders(<Button>Default Button</Button>);

			const button = screen.getByRole("button", { name: /default button/i });
			expect(button).toBeInTheDocument();
		});

		it("applies custom className", () => {
			renderWithProviders(<Button className="custom-class">Custom</Button>);

			const button = screen.getByRole("button", { name: /custom/i });
			expect(button).toHaveClass("custom-class");
		});
	});

	// ===========================================================================
	// Variant Tests
	// ===========================================================================

	describe("variants", () => {
		it.each([
			"primary",
			"secondary",
			"outline",
			"ghost",
			"danger",
			"success",
		] as const)("renders %s variant", (variant) => {
			renderWithProviders(<Button variant={variant}>{variant} button</Button>);

			expect(screen.getByRole("button", { name: new RegExp(variant, "i") })).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Size Tests
	// ===========================================================================

	describe("sizes", () => {
		it.each(["sm", "md", "lg", "icon", "icon-sm"] as const)("renders %s size", (size) => {
			renderWithProviders(<Button size={size}>{size}</Button>);

			expect(screen.getByRole("button", { name: new RegExp(size, "i") })).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Interaction Tests
	// ===========================================================================

	describe("interactions", () => {
		it("calls onPress when clicked", async () => {
			const handlePress = vi.fn();
			const { user } = renderWithProviders(<Button onPress={handlePress}>Click me</Button>);

			const button = screen.getByRole("button", { name: /click me/i });
			await user.click(button);

			expect(handlePress).toHaveBeenCalledTimes(1);
		});

		it("does not call onPress when disabled", async () => {
			const handlePress = vi.fn();
			const { user } = renderWithProviders(
				<Button onPress={handlePress} isDisabled>
					Disabled
				</Button>,
			);

			const button = screen.getByRole("button", { name: /disabled/i });
			await user.click(button);

			expect(handlePress).not.toHaveBeenCalled();
		});

		it("supports keyboard activation with Enter", async () => {
			const handlePress = vi.fn();
			const { user } = renderWithProviders(<Button onPress={handlePress}>Press me</Button>);

			const button = screen.getByRole("button", { name: /press me/i });
			await user.tab();
			expect(button).toHaveFocus();
			await user.keyboard("{Enter}");

			expect(handlePress).toHaveBeenCalledTimes(1);
		});

		it("supports keyboard activation with Space", async () => {
			const handlePress = vi.fn();
			const { user } = renderWithProviders(<Button onPress={handlePress}>Press me</Button>);

			const button = screen.getByRole("button", { name: /press me/i });
			await user.tab();
			expect(button).toHaveFocus();
			await user.keyboard(" ");

			expect(handlePress).toHaveBeenCalledTimes(1);
		});
	});

	// ===========================================================================
	// Disabled State Tests
	// ===========================================================================

	describe("disabled state", () => {
		it("renders as disabled when isDisabled is true", () => {
			renderWithProviders(<Button isDisabled>Disabled</Button>);

			const button = screen.getByRole("button", { name: /disabled/i });
			expect(button).toBeDisabled();
		});

		it("has disabled styling when isDisabled is true", () => {
			renderWithProviders(<Button isDisabled>Disabled</Button>);

			const button = screen.getByRole("button", { name: /disabled/i });
			expect(button).toHaveClass("disabled:opacity-50");
			expect(button).toHaveClass("disabled:cursor-not-allowed");
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("has accessible role of button", () => {
			renderWithProviders(<Button>Accessible</Button>);

			expect(screen.getByRole("button")).toBeInTheDocument();
		});

		it("supports aria-label", () => {
			renderWithProviders(<Button aria-label="Close dialog">X</Button>);

			expect(screen.getByRole("button", { name: /close dialog/i })).toBeInTheDocument();
		});

		it("is focusable", async () => {
			const { user } = renderWithProviders(<Button>Focusable</Button>);

			const button = screen.getByRole("button", { name: /focusable/i });
			await user.tab();

			expect(button).toHaveFocus();
		});

		it("is not focusable when disabled", () => {
			renderWithProviders(<Button isDisabled>Not Focusable</Button>);

			const button = screen.getByRole("button", { name: /not focusable/i });
			expect(button).toBeDisabled();
		});
	});
});

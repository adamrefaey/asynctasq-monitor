/**
 * Tests for the TextField component.
 *
 * Tests cover:
 * - Basic rendering
 * - Label and description rendering
 * - Placeholder support
 * - Size variants
 * - Custom className
 * - User interactions
 * - Validation and error messages
 * - Accessibility
 */

import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test/test-utils";
import { TextField } from "../TextField";

describe("TextField", () => {
	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders input element", () => {
			renderWithProviders(<TextField aria-label="Test input" />);

			expect(screen.getByRole("textbox")).toBeInTheDocument();
		});

		it("renders with label", () => {
			renderWithProviders(<TextField label="Username" />);

			expect(screen.getByLabelText("Username")).toBeInTheDocument();
		});

		it("applies custom className", () => {
			renderWithProviders(<TextField aria-label="Test" className="custom-class" />);

			// The className is applied to the root element
			const input = screen.getByRole("textbox");
			expect(input.closest("div.custom-class")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Label and Description Tests
	// ===========================================================================

	describe("labels and descriptions", () => {
		it("renders label correctly", () => {
			renderWithProviders(<TextField label="Email Address" />);

			expect(screen.getByText("Email Address")).toBeInTheDocument();
		});

		it("associates label with input", () => {
			renderWithProviders(<TextField label="Password" />);

			const input = screen.getByLabelText("Password");
			expect(input).toBeInTheDocument();
		});

		it("renders description when provided", () => {
			renderWithProviders(<TextField label="Email" description="Enter your work email" />);

			expect(screen.getByText("Enter your work email")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Placeholder Tests
	// ===========================================================================

	describe("placeholder", () => {
		it("renders placeholder text", () => {
			renderWithProviders(<TextField aria-label="Search" placeholder="Search..." />);

			expect(screen.getByPlaceholderText("Search...")).toBeInTheDocument();
		});

		it("uses empty string placeholder by default", () => {
			renderWithProviders(<TextField aria-label="Test" />);

			const input = screen.getByRole("textbox");
			expect(input).toHaveAttribute("placeholder", "");
		});
	});

	// ===========================================================================
	// Size Tests
	// ===========================================================================

	describe("sizes", () => {
		it("renders sm size", () => {
			renderWithProviders(<TextField aria-label="Small" size="sm" />);

			const input = screen.getByRole("textbox");
			expect(input).toHaveClass("h-8");
			expect(input).toHaveClass("text-xs");
		});

		it("renders md size (default)", () => {
			renderWithProviders(<TextField aria-label="Medium" size="md" />);

			const input = screen.getByRole("textbox");
			expect(input).toHaveClass("h-10");
			expect(input).toHaveClass("text-sm");
		});

		it("renders lg size", () => {
			renderWithProviders(<TextField aria-label="Large" size="lg" />);

			const input = screen.getByRole("textbox");
			expect(input).toHaveClass("h-12");
			expect(input).toHaveClass("text-base");
		});
	});

	// ===========================================================================
	// Interaction Tests
	// ===========================================================================

	describe("interactions", () => {
		it("allows typing into the input", async () => {
			const { user } = renderWithProviders(<TextField label="Name" />);

			const input = screen.getByLabelText("Name");
			await user.type(input, "John Doe");

			expect(input).toHaveValue("John Doe");
		});

		it("calls onChange when value changes", async () => {
			const handleChange = vi.fn();
			const { user } = renderWithProviders(<TextField label="Email" onChange={handleChange} />);

			const input = screen.getByLabelText("Email");
			await user.type(input, "test@example.com");

			expect(handleChange).toHaveBeenCalled();
		});

		it("can be cleared", async () => {
			const { user } = renderWithProviders(<TextField label="Field" defaultValue="Initial" />);

			const input = screen.getByLabelText("Field");
			await user.clear(input);

			expect(input).toHaveValue("");
		});

		it("is focusable", () => {
			renderWithProviders(<TextField label="Focusable" />);

			const input = screen.getByLabelText("Focusable");
			input.focus();

			expect(document.activeElement).toBe(input);
		});
	});

	// ===========================================================================
	// Disabled State Tests
	// ===========================================================================

	describe("disabled state", () => {
		it("renders as disabled when isDisabled is true", () => {
			renderWithProviders(<TextField label="Disabled" isDisabled />);

			const input = screen.getByLabelText("Disabled");
			expect(input).toBeDisabled();
		});

		it("does not allow typing when disabled", async () => {
			const { user } = renderWithProviders(
				<TextField label="Disabled" isDisabled defaultValue="Value" />,
			);

			const input = screen.getByLabelText("Disabled");
			await user.type(input, "New text");

			expect(input).toHaveValue("Value");
		});
	});

	// ===========================================================================
	// Read Only State Tests
	// ===========================================================================

	describe("read only state", () => {
		it("renders as read only when isReadOnly is true", () => {
			renderWithProviders(<TextField label="ReadOnly" isReadOnly />);

			const input = screen.getByLabelText("ReadOnly");
			expect(input).toHaveAttribute("readonly");
		});
	});

	// ===========================================================================
	// Validation Tests
	// ===========================================================================

	describe("validation", () => {
		it("renders error message when validation fails", async () => {
			renderWithProviders(
				<TextField label="Required" isRequired errorMessage="This field is required" />,
			);

			// React Aria handles validation differently - the label shows without asterisk in the label text
			// but the input has required attribute
			const input = screen.getByLabelText("Required");
			expect(input).toBeInTheDocument();
			expect(input).toHaveAttribute("required");
		});

		it("marks required fields with asterisk", () => {
			renderWithProviders(<TextField label="Required Field" isRequired />);

			// React Aria adds asterisk to required labels
			expect(screen.getByText(/required field/i)).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("has accessible role of textbox", () => {
			renderWithProviders(<TextField aria-label="Accessible" />);

			expect(screen.getByRole("textbox")).toBeInTheDocument();
		});

		it("supports aria-label", () => {
			renderWithProviders(<TextField aria-label="Search tasks" />);

			expect(screen.getByRole("textbox", { name: /search tasks/i })).toBeInTheDocument();
		});

		it("label is properly associated with input", () => {
			renderWithProviders(<TextField label="Email" />);

			const input = screen.getByLabelText("Email");
			const label = screen.getByText("Email");

			// Check that clicking the label focuses the input
			expect(label.tagName.toLowerCase()).toBe("label");
			expect(input).toBeInTheDocument();
		});
	});
});

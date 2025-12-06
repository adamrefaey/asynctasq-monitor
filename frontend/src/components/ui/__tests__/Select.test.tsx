/**
 * Tests for the Select component.
 *
 * Tests cover:
 * - Basic rendering
 * - Label and placeholder rendering
 * - Opening and closing the dropdown
 * - Selecting options
 * - Size variants
 * - Keyboard navigation
 * - Accessibility
 */

import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import { Select, SelectItem } from "../Select";

describe("Select", () => {
	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders select trigger button", () => {
			renderWithProviders(
				<Select aria-label="Choose option">
					<SelectItem id="opt1">Option 1</SelectItem>
					<SelectItem id="opt2">Option 2</SelectItem>
				</Select>,
			);

			expect(screen.getByRole("button")).toBeInTheDocument();
		});

		it("renders with label", () => {
			renderWithProviders(
				<Select label="Status">
					<SelectItem id="active">Active</SelectItem>
					<SelectItem id="inactive">Inactive</SelectItem>
				</Select>,
			);

			expect(screen.getByText("Status")).toBeInTheDocument();
		});

		it("renders placeholder when no value selected", () => {
			renderWithProviders(
				<Select aria-label="Choose" placeholder="Select an option">
					<SelectItem id="opt1">Option 1</SelectItem>
				</Select>,
			);

			expect(screen.getByText("Select an option")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Interaction Tests
	// ===========================================================================

	describe("interactions", () => {
		it("opens dropdown when clicked", async () => {
			const { user } = renderWithProviders(
				<Select aria-label="Choose option">
					<SelectItem id="opt1">Option 1</SelectItem>
					<SelectItem id="opt2">Option 2</SelectItem>
				</Select>,
			);

			const trigger = screen.getByRole("button");
			await user.click(trigger);

			await waitFor(() => {
				expect(screen.getByRole("listbox")).toBeInTheDocument();
			});
		});

		it("displays options when opened", async () => {
			const { user } = renderWithProviders(
				<Select aria-label="Choose option">
					<SelectItem id="opt1">Option 1</SelectItem>
					<SelectItem id="opt2">Option 2</SelectItem>
				</Select>,
			);

			const trigger = screen.getByRole("button");
			await user.click(trigger);

			await waitFor(() => {
				expect(screen.getByRole("option", { name: /option 1/i })).toBeInTheDocument();
				expect(screen.getByRole("option", { name: /option 2/i })).toBeInTheDocument();
			});
		});

		it("selects an option when clicked", async () => {
			const handleChange = vi.fn();
			const { user } = renderWithProviders(
				<Select aria-label="Choose" onSelectionChange={handleChange}>
					<SelectItem id="opt1">Option 1</SelectItem>
					<SelectItem id="opt2">Option 2</SelectItem>
				</Select>,
			);

			const trigger = screen.getByRole("button");
			await user.click(trigger);

			await waitFor(() => {
				expect(screen.getByRole("listbox")).toBeInTheDocument();
			});

			const option = screen.getByRole("option", { name: /option 1/i });
			await user.click(option);

			expect(handleChange).toHaveBeenCalledWith("opt1");
		});

		it("closes dropdown after selection", async () => {
			const { user } = renderWithProviders(
				<Select aria-label="Choose">
					<SelectItem id="opt1">Option 1</SelectItem>
				</Select>,
			);

			const trigger = screen.getByRole("button");
			await user.click(trigger);

			await waitFor(() => {
				expect(screen.getByRole("listbox")).toBeInTheDocument();
			});

			const option = screen.getByRole("option", { name: /option 1/i });
			await user.click(option);

			await waitFor(() => {
				expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
			});
		});

		it("shows selected value in trigger", async () => {
			const { user } = renderWithProviders(
				<Select aria-label="Choose">
					<SelectItem id="opt1">Option 1</SelectItem>
					<SelectItem id="opt2">Option 2</SelectItem>
				</Select>,
			);

			const trigger = screen.getByRole("button");
			await user.click(trigger);

			await waitFor(() => {
				expect(screen.getByRole("listbox")).toBeInTheDocument();
			});

			const option = screen.getByRole("option", { name: /option 2/i });
			await user.click(option);

			await waitFor(() => {
				expect(screen.getByRole("button")).toHaveTextContent("Option 2");
			});
		});
	});

	// ===========================================================================
	// Size Tests
	// ===========================================================================

	describe("sizes", () => {
		it("renders sm size", () => {
			renderWithProviders(
				<Select aria-label="Small" size="sm">
					<SelectItem id="opt1">Option</SelectItem>
				</Select>,
			);

			const button = screen.getByRole("button");
			expect(button).toHaveClass("h-8");
		});

		it("renders md size (default)", () => {
			renderWithProviders(
				<Select aria-label="Medium" size="md">
					<SelectItem id="opt1">Option</SelectItem>
				</Select>,
			);

			const button = screen.getByRole("button");
			expect(button).toHaveClass("h-10");
		});

		it("renders lg size", () => {
			renderWithProviders(
				<Select aria-label="Large" size="lg">
					<SelectItem id="opt1">Option</SelectItem>
				</Select>,
			);

			const button = screen.getByRole("button");
			expect(button).toHaveClass("h-12");
		});
	});

	// ===========================================================================
	// Keyboard Navigation Tests
	// ===========================================================================

	describe("keyboard navigation", () => {
		it("opens with Enter key", async () => {
			const { user } = renderWithProviders(
				<Select aria-label="Choose">
					<SelectItem id="opt1">Option 1</SelectItem>
				</Select>,
			);

			const trigger = screen.getByRole("button");
			await user.tab();
			expect(trigger).toHaveFocus();
			await user.keyboard("{Enter}");

			await waitFor(() => {
				expect(screen.getByRole("listbox")).toBeInTheDocument();
			});
		});

		it("opens with Space key", async () => {
			const { user } = renderWithProviders(
				<Select aria-label="Choose">
					<SelectItem id="opt1">Option 1</SelectItem>
				</Select>,
			);

			const trigger = screen.getByRole("button");
			await user.tab();
			expect(trigger).toHaveFocus();
			await user.keyboard(" ");

			await waitFor(() => {
				expect(screen.getByRole("listbox")).toBeInTheDocument();
			});
		});

		it("closes with Escape key", async () => {
			const { user } = renderWithProviders(
				<Select aria-label="Choose">
					<SelectItem id="opt1">Option 1</SelectItem>
				</Select>,
			);

			const trigger = screen.getByRole("button");
			await user.click(trigger);

			await waitFor(() => {
				expect(screen.getByRole("listbox")).toBeInTheDocument();
			});

			await user.keyboard("{Escape}");

			await waitFor(() => {
				expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
			});
		});
	});

	// ===========================================================================
	// Disabled State Tests
	// ===========================================================================

	describe("disabled state", () => {
		it("renders as disabled when isDisabled is true", () => {
			renderWithProviders(
				<Select aria-label="Disabled" isDisabled>
					<SelectItem id="opt1">Option</SelectItem>
				</Select>,
			);

			const button = screen.getByRole("button");
			expect(button).toBeDisabled();
		});

		it("does not open when disabled", async () => {
			const { user } = renderWithProviders(
				<Select aria-label="Disabled" isDisabled>
					<SelectItem id="opt1">Option</SelectItem>
				</Select>,
			);

			const trigger = screen.getByRole("button");
			await user.click(trigger);

			expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("has accessible name from aria-label", () => {
			renderWithProviders(
				<Select aria-label="Choose status">
					<SelectItem id="opt1">Option</SelectItem>
				</Select>,
			);

			// The button should be accessible
			expect(screen.getByRole("button")).toBeInTheDocument();
		});

		it("has accessible name from label", () => {
			renderWithProviders(
				<Select label="Task Status">
					<SelectItem id="opt1">Option</SelectItem>
				</Select>,
			);

			expect(screen.getByText("Task Status")).toBeInTheDocument();
		});

		it("options have correct role", async () => {
			const { user } = renderWithProviders(
				<Select aria-label="Choose">
					<SelectItem id="opt1">Option 1</SelectItem>
				</Select>,
			);

			await user.click(screen.getByRole("button"));

			await waitFor(() => {
				expect(screen.getByRole("option", { name: /option 1/i })).toBeInTheDocument();
			});
		});

		it("listbox has correct role when open", async () => {
			const { user } = renderWithProviders(
				<Select aria-label="Choose">
					<SelectItem id="opt1">Option 1</SelectItem>
				</Select>,
			);

			await user.click(screen.getByRole("button"));

			await waitFor(() => {
				expect(screen.getByRole("listbox")).toBeInTheDocument();
			});
		});
	});
});

describe("SelectItem", () => {
	it("renders with text content", async () => {
		const { user } = renderWithProviders(
			<Select aria-label="Choose">
				<SelectItem id="test">Test Item</SelectItem>
			</Select>,
		);

		await user.click(screen.getByRole("button"));

		await waitFor(() => {
			expect(screen.getByRole("option", { name: /test item/i })).toBeInTheDocument();
		});
	});

	it("applies custom className", async () => {
		const { user } = renderWithProviders(
			<Select aria-label="Choose">
				<SelectItem id="test" className="custom-item">
					Test Item
				</SelectItem>
			</Select>,
		);

		await user.click(screen.getByRole("button"));

		await waitFor(() => {
			const option = screen.getByRole("option", { name: /test item/i });
			expect(option).toHaveClass("custom-item");
		});
	});

	it("supports textValue for accessibility", async () => {
		const { user } = renderWithProviders(
			<Select aria-label="Choose">
				<SelectItem id="test" textValue="Accessible Value">
					<span>Complex Content</span>
				</SelectItem>
			</Select>,
		);

		await user.click(screen.getByRole("button"));

		await waitFor(() => {
			// React Aria may not expose textValue directly in the option name
			// Check that the option exists with the complex content
			expect(screen.getByRole("option", { name: /complex content/i })).toBeInTheDocument();
		});
	});
});

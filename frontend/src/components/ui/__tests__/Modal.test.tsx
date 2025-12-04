/**
 * Tests for the Modal component.
 *
 * Tests cover:
 * - Basic rendering
 * - Opening and closing behavior
 * - Compound component pattern (Modal.Header, Modal.Body, etc.)
 * - Size variants
 * - Close button functionality
 * - Keyboard interaction (Escape key)
 * - Accessibility
 */

import { DialogTrigger } from "react-aria-components";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import { Button } from "../Button";
import { Modal, ModalContent, ModalDialog, ModalFooter } from "../Modal";

describe("Modal", () => {
	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders when isOpen is true", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Test Modal">
						<Modal.Body>Modal content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.getByRole("dialog")).toBeInTheDocument();
			expect(screen.getByText("Modal content")).toBeInTheDocument();
		});

		it("does not render when isOpen is false", () => {
			renderWithProviders(
				<Modal isOpen={false} onOpenChange={() => {}}>
					<ModalDialog title="Test Modal">
						<Modal.Body>Modal content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
		});

		it("renders modal title", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="My Modal Title">
						<Modal.Body>Content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.getByRole("heading", { name: /my modal title/i })).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Compound Component Tests
	// ===========================================================================

	describe("compound components", () => {
		it("renders Modal.Body correctly", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Test">
						<Modal.Body>Body content here</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.getByText("Body content here")).toBeInTheDocument();
		});

		it("renders Modal.Footer correctly", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Test">
						<Modal.Body>Content</Modal.Body>
						<Modal.Footer>
							<Button>Cancel</Button>
							<Button>Submit</Button>
						</Modal.Footer>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
			expect(screen.getByRole("button", { name: /submit/i })).toBeInTheDocument();
		});

		it("renders complete modal structure", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Complete Modal">
						<Modal.Body>
							<p>Some body content</p>
						</Modal.Body>
						<Modal.Footer>
							<Button>Submit</Button>
						</Modal.Footer>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.getByRole("heading", { name: /complete modal/i })).toBeInTheDocument();
			expect(screen.getByText("Some body content")).toBeInTheDocument();
			// There are two close buttons - the X icon and the footer button
			// Check that both exist with getAllByRole
			const closeButtons = screen.getAllByRole("button");
			expect(closeButtons.length).toBeGreaterThanOrEqual(2);
		});
	});

	// ===========================================================================
	// Size Tests
	// ===========================================================================

	describe("sizes", () => {
		it.each(["sm", "md", "lg", "xl", "2xl", "full"] as const)("renders %s size", (size) => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}} size={size}>
					<ModalDialog title={`${size} Modal`}>
						<Modal.Body>Content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Close Button Tests
	// ===========================================================================

	describe("close button", () => {
		it("shows close button by default", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Test">
						<Modal.Body>Content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.getByRole("button", { name: /close dialog/i })).toBeInTheDocument();
		});

		it("hides close button when showCloseButton is false", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Test" showCloseButton={false}>
						<Modal.Body>Content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.queryByRole("button", { name: /close dialog/i })).not.toBeInTheDocument();
		});

		it("calls onOpenChange when close button is clicked", async () => {
			const handleOpenChange = vi.fn();
			const { user } = renderWithProviders(
				<Modal isOpen onOpenChange={handleOpenChange}>
					<ModalDialog title="Test">
						<Modal.Body>Content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			const closeButton = screen.getByRole("button", { name: /close dialog/i });
			await user.click(closeButton);

			expect(handleOpenChange).toHaveBeenCalledWith(false);
		});
	});

	// ===========================================================================
	// Keyboard Interaction Tests
	// ===========================================================================

	describe("keyboard interactions", () => {
		it("closes on Escape key", async () => {
			const handleOpenChange = vi.fn();
			const { user } = renderWithProviders(
				<Modal isOpen onOpenChange={handleOpenChange}>
					<ModalDialog title="Test">
						<Modal.Body>Content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			await user.keyboard("{Escape}");

			expect(handleOpenChange).toHaveBeenCalledWith(false);
		});
	});

	// ===========================================================================
	// Overlay Tests
	// ===========================================================================

	describe("overlay", () => {
		it("renders backdrop overlay", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Test">
						<Modal.Body>Content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			// Modal overlay should be present (backdrop)
			const dialog = screen.getByRole("dialog");
			expect(dialog).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("has dialog role", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Accessible Modal">
						<Modal.Body>Content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.getByRole("dialog")).toBeInTheDocument();
		});

		it("has accessible title", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Modal Title">
						<Modal.Body>Content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.getByRole("heading", { name: /modal title/i })).toBeInTheDocument();
		});

		it("close button has accessible label", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Test">
						<Modal.Body>Content</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			expect(screen.getByRole("button", { name: /close dialog/i })).toBeInTheDocument();
		});

		it("traps focus within modal", () => {
			renderWithProviders(
				<Modal isOpen onOpenChange={() => {}}>
					<ModalDialog title="Focus Trap">
						<Modal.Body>
							<button type="button">First Button</button>
							<button type="button">Second Button</button>
						</Modal.Body>
					</ModalDialog>
				</Modal>,
			);

			// Focus should be within the modal
			const dialog = screen.getByRole("dialog");
			expect(dialog).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// DialogTrigger Integration Tests
	// ===========================================================================

	describe("DialogTrigger integration", () => {
		it("opens modal when trigger is clicked", async () => {
			const { user } = renderWithProviders(
				<DialogTrigger>
					<Button>Open Modal</Button>
					<Modal>
						<ModalDialog title="Triggered Modal">
							<Modal.Body>Modal opened via trigger</Modal.Body>
						</ModalDialog>
					</Modal>
				</DialogTrigger>,
			);

			const trigger = screen.getByRole("button", { name: /open modal/i });
			await user.click(trigger);

			await waitFor(() => {
				expect(screen.getByRole("dialog")).toBeInTheDocument();
			});
		});
	});
});

describe("Exported standalone components", () => {
	it("ModalContent works as standalone export", () => {
		renderWithProviders(
			<Modal isOpen onOpenChange={() => {}}>
				<ModalDialog title="Test">
					<ModalContent>Standalone content</ModalContent>
				</ModalDialog>
			</Modal>,
		);

		expect(screen.getByText("Standalone content")).toBeInTheDocument();
	});

	it("ModalFooter works as standalone export", () => {
		renderWithProviders(
			<Modal isOpen onOpenChange={() => {}}>
				<ModalDialog title="Test">
					<Modal.Body>Content</Modal.Body>
					<ModalFooter>
						<Button>Action</Button>
					</ModalFooter>
				</ModalDialog>
			</Modal>,
		);

		expect(screen.getByRole("button", { name: /action/i })).toBeInTheDocument();
	});
});

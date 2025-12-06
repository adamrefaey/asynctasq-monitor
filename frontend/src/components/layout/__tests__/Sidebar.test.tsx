/**
 * Tests for the Sidebar component.
 *
 * Tests cover:
 * - Basic rendering
 * - Navigation links
 * - Active state styling
 * - Logo and branding
 * - Version footer
 * - Accessibility
 */

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Sidebar } from "../Sidebar";

// Helper to render with router at specific path
function renderWithRouter(initialPath = "/") {
	return render(
		<MemoryRouter
			initialEntries={[initialPath]}
			future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
		>
			<Sidebar />
		</MemoryRouter>,
	);
}

describe("Sidebar", () => {
	// ===========================================================================
	// Basic Rendering Tests
	// ===========================================================================

	describe("rendering", () => {
		it("renders aside element", () => {
			renderWithRouter();

			expect(screen.getByRole("complementary")).toBeInTheDocument();
		});

		it("renders navigation element", () => {
			renderWithRouter();

			expect(screen.getByRole("navigation")).toBeInTheDocument();
		});

		it("renders logo section", () => {
			renderWithRouter();

			// Logo has "Q" letter
			expect(screen.getByText("Q")).toBeInTheDocument();
			expect(screen.getByText("Task Monitor")).toBeInTheDocument();
		});

		it("renders version footer", () => {
			renderWithRouter();

			expect(screen.getByText("async-task-q-monitor")).toBeInTheDocument();
			expect(screen.getByText("v1.0.0")).toBeInTheDocument();
		});
	});

	// ===========================================================================
	// Navigation Links Tests
	// ===========================================================================

	describe("navigation links", () => {
		it.each([
			{ name: "Dashboard", href: "/" },
			{ name: "Tasks", href: "/tasks" },
			{ name: "Workers", href: "/workers" },
			{ name: "Queues", href: "/queues" },
			{ name: "Metrics", href: "/metrics" },
			{ name: "Settings", href: "/settings" },
		])("renders $name link", ({ name, href }) => {
			renderWithRouter();

			const link = screen.getByRole("link", { name });
			expect(link).toBeInTheDocument();
			expect(link).toHaveAttribute("href", href);
		});

		it("renders all navigation items", () => {
			renderWithRouter();

			const navLinks = screen.getAllByRole("link");
			expect(navLinks).toHaveLength(6);
		});
	});

	// ===========================================================================
	// Active State Tests
	// ===========================================================================

	describe("active state", () => {
		it("marks Dashboard as active on root path", () => {
			renderWithRouter("/");

			const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
			expect(dashboardLink).toHaveClass("bg-blue-50", "text-blue-700");
		});

		it("marks Tasks as active on tasks path", () => {
			renderWithRouter("/tasks");

			const tasksLink = screen.getByRole("link", { name: "Tasks" });
			expect(tasksLink).toHaveClass("bg-blue-50", "text-blue-700");
		});

		it("marks Workers as active on workers path", () => {
			renderWithRouter("/workers");

			const workersLink = screen.getByRole("link", { name: "Workers" });
			expect(workersLink).toHaveClass("bg-blue-50", "text-blue-700");
		});

		it("marks Queues as active on queues path", () => {
			renderWithRouter("/queues");

			const queuesLink = screen.getByRole("link", { name: "Queues" });
			expect(queuesLink).toHaveClass("bg-blue-50", "text-blue-700");
		});

		it("marks Metrics as active on metrics path", () => {
			renderWithRouter("/metrics");

			const metricsLink = screen.getByRole("link", { name: "Metrics" });
			expect(metricsLink).toHaveClass("bg-blue-50", "text-blue-700");
		});

		it("marks Settings as active on settings path", () => {
			renderWithRouter("/settings");

			const settingsLink = screen.getByRole("link", { name: "Settings" });
			expect(settingsLink).toHaveClass("bg-blue-50", "text-blue-700");
		});

		it("marks parent route active for nested paths", () => {
			renderWithRouter("/tasks/123");

			const tasksLink = screen.getByRole("link", { name: "Tasks" });
			expect(tasksLink).toHaveClass("bg-blue-50", "text-blue-700");
		});

		it("inactive links have default styling", () => {
			renderWithRouter("/");

			const tasksLink = screen.getByRole("link", { name: "Tasks" });
			expect(tasksLink).toHaveClass("text-zinc-600");
			expect(tasksLink).not.toHaveClass("bg-blue-50");
		});
	});

	// ===========================================================================
	// Icon Tests
	// ===========================================================================

	describe("icons", () => {
		it("renders icons with aria-hidden", () => {
			renderWithRouter();

			// All nav icons should be hidden from screen readers
			const navLinks = screen.getAllByRole("link");
			for (const link of navLinks) {
				const svg = link.querySelector("svg");
				if (svg) {
					expect(svg).toHaveAttribute("aria-hidden", "true");
				}
			}
		});
	});

	// ===========================================================================
	// Accessibility Tests
	// ===========================================================================

	describe("accessibility", () => {
		it("has complementary role for aside", () => {
			renderWithRouter();

			expect(screen.getByRole("complementary")).toBeInTheDocument();
		});

		it("has navigation role for nav", () => {
			renderWithRouter();

			expect(screen.getByRole("navigation")).toBeInTheDocument();
		});

		it("all links are accessible", () => {
			renderWithRouter();

			const links = screen.getAllByRole("link");
			for (const link of links) {
				expect(link).toHaveAccessibleName();
			}
		});

		it("links have visible focus styles", () => {
			renderWithRouter();

			const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
			// Check for focus-visible ring class
			expect(dashboardLink).toHaveClass("focus-visible:ring-2");
		});
	});
});

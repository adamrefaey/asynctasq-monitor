/**
 * Vitest test setup file.
 * Configures jest-dom matchers and automatic cleanup.
 */

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Automatic cleanup after each test
afterEach(() => {
	cleanup();
});

// Mock window.matchMedia for components that use media queries
Object.defineProperty(window, "matchMedia", {
	writable: true,
	value: vi.fn().mockImplementation((query: string) => ({
		matches: false,
		media: query,
		onchange: null,
		addListener: vi.fn(), // Deprecated
		removeListener: vi.fn(), // Deprecated
		addEventListener: vi.fn(),
		removeEventListener: vi.fn(),
		dispatchEvent: vi.fn(),
	})),
});

// Mock ResizeObserver for components that depend on it
class MockResizeObserver {
	observe = vi.fn();
	unobserve = vi.fn();
	disconnect = vi.fn();
}

Object.defineProperty(window, "ResizeObserver", {
	writable: true,
	value: MockResizeObserver,
});

// Mock IntersectionObserver for lazy-loaded components
class MockIntersectionObserver {
	observe = vi.fn();
	unobserve = vi.fn();
	disconnect = vi.fn();
	root = null;
	rootMargin = "";
	thresholds = [];
}

Object.defineProperty(window, "IntersectionObserver", {
	writable: true,
	value: MockIntersectionObserver,
});

// Suppress console warnings for SVG elements and Recharts dimension issues in JSDOM
// biome-ignore lint/suspicious/noConsole: Intentionally capturing console methods to filter test noise
const originalError = console.error;
// biome-ignore lint/suspicious/noConsole: Intentionally capturing console methods to filter test noise
const originalWarn = console.warn;

const suppressedPatterns = [
	"is unrecognized in this browser",
	"is using incorrect casing",
	"width(-1)",
	"width(0)",
	"height(-1)",
	"height(0)",
	"should be greater than 0",
];

function shouldSuppress(message: string): boolean {
	return suppressedPatterns.some((pattern) => message.includes(pattern));
}

console.error = (...args: unknown[]) => {
	const message = typeof args[0] === "string" ? args[0] : "";
	if (shouldSuppress(message)) return;
	originalError.apply(console, args);
};

console.warn = (...args: unknown[]) => {
	const message = typeof args[0] === "string" ? args[0] : "";
	if (shouldSuppress(message)) return;
	originalWarn.apply(console, args);
};

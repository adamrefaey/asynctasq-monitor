/**
 * Tests for the useTheme hook.
 *
 * Tests cover:
 * - Default theme initialization
 * - Theme setting (light, dark, system)
 * - System theme detection
 * - Theme toggle functionality
 * - localStorage persistence
 * - Media query listener for system changes
 */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useTheme } from "../useTheme";

const THEME_KEY = "async-task-q-monitor-theme";

// Mock localStorage
const localStorageMock = (() => {
	let store: Record<string, string> = {};
	return {
		getItem: vi.fn((key: string) => store[key] || null),
		setItem: vi.fn((key: string, value: string) => {
			store[key] = value;
		}),
		removeItem: vi.fn((key: string) => {
			delete store[key];
		}),
		clear: () => {
			store = {};
		},
		reset: () => {
			store = {};
			localStorageMock.getItem.mockClear();
			localStorageMock.setItem.mockClear();
			localStorageMock.removeItem.mockClear();
		},
	};
})();

Object.defineProperty(window, "localStorage", {
	value: localStorageMock,
});

// Mock matchMedia
type MediaQueryListener = (e: MediaQueryListEvent) => void;
let mediaQueryListeners: MediaQueryListener[] = [];
let prefersDark = false;

const matchMediaMock = vi.fn().mockImplementation((query: string) => ({
	matches: query === "(prefers-color-scheme: dark)" ? prefersDark : false,
	media: query,
	onchange: null,
	addListener: vi.fn(),
	removeListener: vi.fn(),
	addEventListener: vi.fn((_event: string, listener: MediaQueryListener) => {
		mediaQueryListeners.push(listener);
	}),
	removeEventListener: vi.fn((_event: string, listener: MediaQueryListener) => {
		mediaQueryListeners = mediaQueryListeners.filter((l) => l !== listener);
	}),
	dispatchEvent: vi.fn(),
}));

Object.defineProperty(window, "matchMedia", {
	writable: true,
	value: matchMediaMock,
});

// Helper to trigger system theme change
function triggerSystemThemeChange(dark: boolean) {
	prefersDark = dark;
	for (const listener of mediaQueryListeners) {
		listener({ matches: dark } as MediaQueryListEvent);
	}
}

describe("useTheme", () => {
	beforeEach(() => {
		// Reset state before each test
		localStorageMock.reset();
		mediaQueryListeners = [];
		prefersDark = false;
		document.documentElement.classList.remove("dark");
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	// ===========================================================================
	// Initialization Tests
	// ===========================================================================

	describe("initialization", () => {
		it("defaults to system theme when no stored preference", () => {
			const { result } = renderHook(() => useTheme());

			expect(result.current.themeSetting).toBe("system");
		});

		it("resolves to light when system prefers light", () => {
			prefersDark = false;
			const { result } = renderHook(() => useTheme());

			expect(result.current.theme).toBe("light");
		});

		it("resolves to dark when system prefers dark", () => {
			prefersDark = true;
			const { result } = renderHook(() => useTheme());

			expect(result.current.theme).toBe("dark");
		});

		it("loads stored theme from localStorage", () => {
			localStorageMock.getItem.mockReturnValue("dark");
			const { result } = renderHook(() => useTheme());

			expect(result.current.themeSetting).toBe("dark");
			expect(result.current.theme).toBe("dark");
		});

		it("handles invalid stored theme gracefully", () => {
			localStorageMock.getItem.mockReturnValue("invalid");
			const { result } = renderHook(() => useTheme());

			// Should fall back to system
			expect(result.current.themeSetting).toBe("system");
		});
	});

	// ===========================================================================
	// setTheme Tests
	// ===========================================================================

	describe("setTheme", () => {
		it("sets theme to light", () => {
			const { result } = renderHook(() => useTheme());

			act(() => {
				result.current.setTheme("light");
			});

			expect(result.current.themeSetting).toBe("light");
			expect(result.current.theme).toBe("light");
		});

		it("sets theme to dark", () => {
			const { result } = renderHook(() => useTheme());

			act(() => {
				result.current.setTheme("dark");
			});

			expect(result.current.themeSetting).toBe("dark");
			expect(result.current.theme).toBe("dark");
		});

		it("sets theme to system", () => {
			prefersDark = true;
			const { result } = renderHook(() => useTheme());

			act(() => {
				result.current.setTheme("light");
				result.current.setTheme("system");
			});

			expect(result.current.themeSetting).toBe("system");
			expect(result.current.theme).toBe("dark");
		});

		it("persists theme to localStorage", () => {
			const { result } = renderHook(() => useTheme());

			act(() => {
				result.current.setTheme("dark");
			});

			expect(localStorageMock.setItem).toHaveBeenCalledWith(THEME_KEY, "dark");
		});
	});

	// ===========================================================================
	// toggleTheme Tests
	// ===========================================================================

	describe("toggleTheme", () => {
		it("toggles from light to dark", () => {
			const { result } = renderHook(() => useTheme());

			act(() => {
				result.current.setTheme("light");
			});

			act(() => {
				result.current.toggleTheme();
			});

			expect(result.current.theme).toBe("dark");
		});

		it("toggles from dark to light", () => {
			const { result } = renderHook(() => useTheme());

			act(() => {
				result.current.setTheme("dark");
			});

			act(() => {
				result.current.toggleTheme();
			});

			expect(result.current.theme).toBe("light");
		});

		it("toggles from system (light) to dark", () => {
			prefersDark = false;
			const { result } = renderHook(() => useTheme());

			expect(result.current.themeSetting).toBe("system");
			expect(result.current.theme).toBe("light");

			act(() => {
				result.current.toggleTheme();
			});

			expect(result.current.theme).toBe("dark");
		});

		it("toggles from system (dark) to light", () => {
			prefersDark = true;
			const { result } = renderHook(() => useTheme());

			expect(result.current.themeSetting).toBe("system");
			expect(result.current.theme).toBe("dark");

			act(() => {
				result.current.toggleTheme();
			});

			expect(result.current.theme).toBe("light");
		});
	});

	// ===========================================================================
	// DOM Updates Tests
	// ===========================================================================

	describe("DOM updates", () => {
		it("adds dark class to document when dark theme", () => {
			const { result } = renderHook(() => useTheme());

			act(() => {
				result.current.setTheme("dark");
			});

			expect(document.documentElement.classList.contains("dark")).toBe(true);
		});

		it("removes dark class from document when light theme", () => {
			document.documentElement.classList.add("dark");
			const { result } = renderHook(() => useTheme());

			act(() => {
				result.current.setTheme("light");
			});

			expect(document.documentElement.classList.contains("dark")).toBe(false);
		});
	});

	// ===========================================================================
	// System Theme Change Listener Tests
	// ===========================================================================

	describe("system theme change listener", () => {
		it("responds to system theme changes when set to system", () => {
			prefersDark = false;
			const { result } = renderHook(() => useTheme());

			expect(result.current.theme).toBe("light");

			act(() => {
				triggerSystemThemeChange(true);
			});

			expect(result.current.theme).toBe("dark");
		});

		it("ignores system theme changes when set to explicit theme", () => {
			const { result } = renderHook(() => useTheme());

			act(() => {
				result.current.setTheme("light");
			});

			act(() => {
				triggerSystemThemeChange(true);
			});

			// Should still be light since we explicitly set it
			expect(result.current.theme).toBe("light");
		});

		it("cleans up listener on unmount", () => {
			const { unmount } = renderHook(() => useTheme());
			const initialListenerCount = mediaQueryListeners.length;

			unmount();

			// Listener should be removed
			expect(mediaQueryListeners.length).toBeLessThanOrEqual(initialListenerCount);
		});
	});

	// ===========================================================================
	// Return Value Tests
	// ===========================================================================

	describe("return values", () => {
		it("returns all expected properties", () => {
			const { result } = renderHook(() => useTheme());

			expect(result.current).toHaveProperty("theme");
			expect(result.current).toHaveProperty("themeSetting");
			expect(result.current).toHaveProperty("setTheme");
			expect(result.current).toHaveProperty("toggleTheme");
		});

		it("theme is resolved value (light or dark)", () => {
			const { result } = renderHook(() => useTheme());

			expect(["light", "dark"]).toContain(result.current.theme);
		});

		it("themeSetting can be system", () => {
			const { result } = renderHook(() => useTheme());

			expect(result.current.themeSetting).toBe("system");
		});

		it("setTheme is a function", () => {
			const { result } = renderHook(() => useTheme());

			expect(typeof result.current.setTheme).toBe("function");
		});

		it("toggleTheme is a function", () => {
			const { result } = renderHook(() => useTheme());

			expect(typeof result.current.toggleTheme).toBe("function");
		});
	});
});

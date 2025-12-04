/**
 * Tests for the useSettings hook and Zustand store.
 *
 * Tests cover:
 * - Default state values
 * - Individual setter actions
 * - Toggle actions
 * - Reset to defaults
 * - Clear all data
 * - Selector hooks
 * - localStorage persistence
 */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
	useDateFormatSetting,
	useItemsPerPage,
	useRefreshInterval,
	useSettingsStore,
	useTableDensity,
	useThemeSetting,
	useTimezone,
} from "../useSettings";

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
		clear: vi.fn(() => {
			store = {};
		}),
	};
})();

Object.defineProperty(window, "localStorage", {
	value: localStorageMock,
});

describe("useSettings", () => {
	beforeEach(() => {
		// Reset store state before each test
		const { result } = renderHook(() => useSettingsStore());
		act(() => {
			result.current.resetToDefaults();
		});
		localStorageMock.clear();
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	// ===========================================================================
	// Default State Tests
	// ===========================================================================

	describe("default state", () => {
		it("has correct default theme setting", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.theme).toBe("system");
		});

		it("has correct default timezone", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.timezone).toBe("UTC");
		});

		it("has correct default date format", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.dateFormat).toBe("relative");
		});

		it("has correct default refresh interval", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.refreshInterval).toBe(5);
		});

		it("has correct default table density", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.tableDensity).toBe("comfortable");
		});

		it("has correct default items per page", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.itemsPerPage).toBe(25);
		});

		it("has sidebar expanded by default", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.sidebarExpanded).toBe(true);
		});

		it("has notifications enabled by default", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.enableNotifications).toBe(true);
		});

		it("has notify on failure enabled by default", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.notifyOnFailure).toBe(true);
		});

		it("has notify on complete disabled by default", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.notifyOnComplete).toBe(false);
		});

		it("has sound disabled by default", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.soundEnabled).toBe(false);
		});

		it("has debug mode disabled by default", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.debugMode).toBe(false);
		});

		it("has cache enabled by default", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.cacheEnabled).toBe(true);
		});

		it("has correct default max retries", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.maxRetries).toBe(3);
		});

		it("has correct default log level", () => {
			const { result } = renderHook(() => useSettingsStore());
			expect(result.current.logLevel).toBe("info");
		});
	});

	// ===========================================================================
	// Theme Actions Tests
	// ===========================================================================

	describe("theme actions", () => {
		it("sets theme to light", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setTheme("light");
			});

			expect(result.current.theme).toBe("light");
		});

		it("sets theme to dark", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setTheme("dark");
			});

			expect(result.current.theme).toBe("dark");
		});

		it("sets theme to system", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setTheme("dark");
				result.current.setTheme("system");
			});

			expect(result.current.theme).toBe("system");
		});
	});

	// ===========================================================================
	// General Setting Actions Tests
	// ===========================================================================

	describe("general setting actions", () => {
		it("sets timezone", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setTimezone("America/New_York");
			});

			expect(result.current.timezone).toBe("America/New_York");
		});

		it("sets date format to absolute", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setDateFormat("absolute");
			});

			expect(result.current.dateFormat).toBe("absolute");
		});

		it("sets refresh interval", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setRefreshInterval(10);
			});

			expect(result.current.refreshInterval).toBe(10);
		});
	});

	// ===========================================================================
	// Display Setting Actions Tests
	// ===========================================================================

	describe("display setting actions", () => {
		it("sets table density to compact", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setTableDensity("compact");
			});

			expect(result.current.tableDensity).toBe("compact");
		});

		it("sets table density to spacious", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setTableDensity("spacious");
			});

			expect(result.current.tableDensity).toBe("spacious");
		});

		it("sets items per page", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setItemsPerPage(50);
			});

			expect(result.current.itemsPerPage).toBe(50);
		});

		it("sets sidebar expanded state", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setSidebarExpanded(false);
			});

			expect(result.current.sidebarExpanded).toBe(false);
		});

		it("toggles sidebar state", () => {
			const { result } = renderHook(() => useSettingsStore());

			expect(result.current.sidebarExpanded).toBe(true);

			act(() => {
				result.current.toggleSidebar();
			});

			expect(result.current.sidebarExpanded).toBe(false);

			act(() => {
				result.current.toggleSidebar();
			});

			expect(result.current.sidebarExpanded).toBe(true);
		});
	});

	// ===========================================================================
	// Connection Setting Actions Tests
	// ===========================================================================

	describe("connection setting actions", () => {
		it("sets API URL", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setApiUrl("http://api.example.com");
			});

			expect(result.current.apiUrl).toBe("http://api.example.com");
		});

		it("sets WebSocket URL", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setWsUrl("ws://ws.example.com");
			});

			expect(result.current.wsUrl).toBe("ws://ws.example.com");
		});

		it("sets timeout", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setTimeout(60);
			});

			expect(result.current.timeout).toBe(60);
		});
	});

	// ===========================================================================
	// Notification Setting Actions Tests
	// ===========================================================================

	describe("notification setting actions", () => {
		it("sets enable notifications", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setEnableNotifications(false);
			});

			expect(result.current.enableNotifications).toBe(false);
		});

		it("sets notify on failure", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setNotifyOnFailure(false);
			});

			expect(result.current.notifyOnFailure).toBe(false);
		});

		it("sets notify on complete", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setNotifyOnComplete(true);
			});

			expect(result.current.notifyOnComplete).toBe(true);
		});

		it("sets sound enabled", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setSoundEnabled(true);
			});

			expect(result.current.soundEnabled).toBe(true);
		});
	});

	// ===========================================================================
	// Advanced Setting Actions Tests
	// ===========================================================================

	describe("advanced setting actions", () => {
		it("sets debug mode", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setDebugMode(true);
			});

			expect(result.current.debugMode).toBe(true);
		});

		it("sets cache enabled", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setCacheEnabled(false);
			});

			expect(result.current.cacheEnabled).toBe(false);
		});

		it("sets max retries", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setMaxRetries(5);
			});

			expect(result.current.maxRetries).toBe(5);
		});

		it("sets log level", () => {
			const { result } = renderHook(() => useSettingsStore());

			act(() => {
				result.current.setLogLevel("debug");
			});

			expect(result.current.logLevel).toBe("debug");
		});
	});

	// ===========================================================================
	// Bulk Action Tests
	// ===========================================================================

	describe("bulk actions", () => {
		it("resets all settings to defaults", () => {
			const { result } = renderHook(() => useSettingsStore());

			// Modify several settings
			act(() => {
				result.current.setTheme("dark");
				result.current.setTimezone("Asia/Tokyo");
				result.current.setTableDensity("compact");
				result.current.setDebugMode(true);
			});

			// Reset to defaults
			act(() => {
				result.current.resetToDefaults();
			});

			// Verify defaults restored
			expect(result.current.theme).toBe("system");
			expect(result.current.timezone).toBe("UTC");
			expect(result.current.tableDensity).toBe("comfortable");
			expect(result.current.debugMode).toBe(false);
		});

		it("clears all data and removes from localStorage", () => {
			const { result } = renderHook(() => useSettingsStore());

			// Modify settings
			act(() => {
				result.current.setTheme("dark");
			});

			// Clear all data
			act(() => {
				result.current.clearAllData();
			});

			// Verify localStorage.removeItem was called
			expect(localStorageMock.removeItem).toHaveBeenCalledWith("asynctasq-monitor-settings");

			// Verify defaults restored
			expect(result.current.theme).toBe("system");
		});
	});

	// ===========================================================================
	// Selector Hook Tests
	// ===========================================================================

	describe("selector hooks", () => {
		it("useThemeSetting returns current theme", () => {
			const { result: storeResult } = renderHook(() => useSettingsStore());
			const { result: selectorResult } = renderHook(() => useThemeSetting());

			expect(selectorResult.current).toBe("system");

			act(() => {
				storeResult.current.setTheme("dark");
			});

			// Re-render to get updated value
			const { result: updatedResult } = renderHook(() => useThemeSetting());
			expect(updatedResult.current).toBe("dark");
		});

		it("useRefreshInterval returns current refresh interval", () => {
			const { result: storeResult } = renderHook(() => useSettingsStore());
			const { result: selectorResult } = renderHook(() => useRefreshInterval());

			expect(selectorResult.current).toBe(5);

			act(() => {
				storeResult.current.setRefreshInterval(15);
			});

			const { result: updatedResult } = renderHook(() => useRefreshInterval());
			expect(updatedResult.current).toBe(15);
		});

		it("useTableDensity returns current table density", () => {
			const { result: storeResult } = renderHook(() => useSettingsStore());
			const { result: selectorResult } = renderHook(() => useTableDensity());

			expect(selectorResult.current).toBe("comfortable");

			act(() => {
				storeResult.current.setTableDensity("compact");
			});

			const { result: updatedResult } = renderHook(() => useTableDensity());
			expect(updatedResult.current).toBe("compact");
		});

		it("useItemsPerPage returns current items per page", () => {
			const { result: storeResult } = renderHook(() => useSettingsStore());
			const { result: selectorResult } = renderHook(() => useItemsPerPage());

			expect(selectorResult.current).toBe(25);

			act(() => {
				storeResult.current.setItemsPerPage(100);
			});

			const { result: updatedResult } = renderHook(() => useItemsPerPage());
			expect(updatedResult.current).toBe(100);
		});

		it("useDateFormatSetting returns current date format", () => {
			const { result: storeResult } = renderHook(() => useSettingsStore());
			const { result: selectorResult } = renderHook(() => useDateFormatSetting());

			expect(selectorResult.current).toBe("relative");

			act(() => {
				storeResult.current.setDateFormat("absolute");
			});

			const { result: updatedResult } = renderHook(() => useDateFormatSetting());
			expect(updatedResult.current).toBe("absolute");
		});

		it("useTimezone returns current timezone", () => {
			const { result: storeResult } = renderHook(() => useSettingsStore());
			const { result: selectorResult } = renderHook(() => useTimezone());

			expect(selectorResult.current).toBe("UTC");

			act(() => {
				storeResult.current.setTimezone("Europe/London");
			});

			const { result: updatedResult } = renderHook(() => useTimezone());
			expect(updatedResult.current).toBe("Europe/London");
		});
	});
});

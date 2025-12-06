/**
 * Tests for the useDebounce hook.
 *
 * Tests cover:
 * - Basic debouncing behavior
 * - Cleanup on unmount
 * - Multiple rapid updates
 * - Custom delay values
 */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useDebounce, useDebouncedCallback } from "../useDebounce";

describe("useDebounce", () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it("returns initial value immediately", () => {
		const { result } = renderHook(() => useDebounce("initial", 300));
		expect(result.current).toBe("initial");
	});

	it("updates value after delay", async () => {
		const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
			initialProps: { value: "initial" },
		});

		expect(result.current).toBe("initial");

		rerender({ value: "updated" });
		expect(result.current).toBe("initial"); // Still initial

		await act(async () => {
			vi.advanceTimersByTime(300);
		});

		expect(result.current).toBe("updated");
	});

	it("cancels pending update when value changes", async () => {
		const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
			initialProps: { value: "initial" },
		});

		rerender({ value: "first" });
		await act(async () => {
			vi.advanceTimersByTime(100);
		});

		rerender({ value: "second" });
		await act(async () => {
			vi.advanceTimersByTime(100);
		});

		rerender({ value: "third" });
		await act(async () => {
			vi.advanceTimersByTime(300);
		});

		// Should be "third" because previous updates were cancelled
		expect(result.current).toBe("third");
	});

	it("uses default delay of 300ms", async () => {
		const { result, rerender } = renderHook(({ value }) => useDebounce(value), {
			initialProps: { value: "initial" },
		});

		rerender({ value: "updated" });

		await act(async () => {
			vi.advanceTimersByTime(299);
		});
		expect(result.current).toBe("initial");

		await act(async () => {
			vi.advanceTimersByTime(1);
		});
		expect(result.current).toBe("updated");
	});

	it("supports custom delay", async () => {
		const { result, rerender } = renderHook(({ value }) => useDebounce(value, 500), {
			initialProps: { value: "initial" },
		});

		rerender({ value: "updated" });

		await act(async () => {
			vi.advanceTimersByTime(499);
		});
		expect(result.current).toBe("initial");

		await act(async () => {
			vi.advanceTimersByTime(1);
		});
		expect(result.current).toBe("updated");
	});

	it("handles empty string", async () => {
		const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
			initialProps: { value: "initial" },
		});

		rerender({ value: "" });

		await act(async () => {
			vi.advanceTimersByTime(300);
		});

		expect(result.current).toBe("");
	});

	it("handles null values", async () => {
		const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
			initialProps: { value: "initial" as string | null },
		});

		rerender({ value: null });

		await act(async () => {
			vi.advanceTimersByTime(300);
		});

		expect(result.current).toBe(null);
	});

	it("handles object values", async () => {
		const initialObj = { name: "test" };
		const updatedObj = { name: "updated" };

		const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
			initialProps: { value: initialObj },
		});

		rerender({ value: updatedObj });

		await act(async () => {
			vi.advanceTimersByTime(300);
		});

		expect(result.current).toEqual(updatedObj);
	});

	it("clears timeout on unmount", async () => {
		const { unmount, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
			initialProps: { value: "initial" },
		});

		rerender({ value: "updated" });

		// Unmount before timeout completes
		unmount();

		// This should not throw or cause any issues
		await act(async () => {
			vi.advanceTimersByTime(500);
		});
	});
});

describe("useDebouncedCallback", () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it("debounces callback execution", async () => {
		const callback = vi.fn();
		const { result } = renderHook(() => useDebouncedCallback(callback, 300));

		result.current("arg1");

		expect(callback).not.toHaveBeenCalled();

		await act(async () => {
			vi.advanceTimersByTime(300);
		});

		expect(callback).toHaveBeenCalledWith("arg1");
		expect(callback).toHaveBeenCalledTimes(1);
	});

	it("cancels previous callback when called again", async () => {
		const callback = vi.fn();
		const { result } = renderHook(() => useDebouncedCallback(callback, 300));

		result.current("first");
		await act(async () => {
			vi.advanceTimersByTime(100);
		});

		result.current("second");
		await act(async () => {
			vi.advanceTimersByTime(300);
		});

		expect(callback).toHaveBeenCalledWith("second");
		expect(callback).toHaveBeenCalledTimes(1);
	});

	it("passes multiple arguments to callback", async () => {
		const callback = vi.fn();
		const { result } = renderHook(() => useDebouncedCallback(callback, 300));

		result.current("arg1", "arg2", "arg3");

		await act(async () => {
			vi.advanceTimersByTime(300);
		});

		expect(callback).toHaveBeenCalledWith("arg1", "arg2", "arg3");
	});

	it("uses default delay of 300ms", async () => {
		const callback = vi.fn();
		const { result } = renderHook(() => useDebouncedCallback(callback));

		result.current();

		await act(async () => {
			vi.advanceTimersByTime(299);
		});
		expect(callback).not.toHaveBeenCalled();

		await act(async () => {
			vi.advanceTimersByTime(1);
		});
		expect(callback).toHaveBeenCalled();
	});

	it("handles rapid successive calls", async () => {
		const callback = vi.fn();
		const { result } = renderHook(() => useDebouncedCallback(callback, 300));

		// Simulate rapid typing
		for (let i = 0; i < 10; i++) {
			result.current(`value${i}`);
			await act(async () => {
				vi.advanceTimersByTime(50);
			});
		}

		// Wait for final debounce
		await act(async () => {
			vi.advanceTimersByTime(300);
		});

		// Should only be called once with the last value
		expect(callback).toHaveBeenCalledTimes(1);
		expect(callback).toHaveBeenCalledWith("value9");
	});

	it("cleans up timeout on unmount", async () => {
		const callback = vi.fn();
		const { result, unmount } = renderHook(() => useDebouncedCallback(callback, 300));

		result.current("test");
		unmount();

		await act(async () => {
			vi.advanceTimersByTime(500);
		});

		// Callback should not be called after unmount
		expect(callback).not.toHaveBeenCalled();
	});
});

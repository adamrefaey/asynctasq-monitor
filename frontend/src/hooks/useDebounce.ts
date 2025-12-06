/**
 * Debounce hook for delaying value updates.
 *
 * Useful for search inputs and other user inputs that trigger expensive operations.
 * Based on 2024/2025 React best practices for debouncing user input.
 */

import { useEffect, useRef, useState } from "react";

/**
 * Debounces a value, only updating after the specified delay.
 *
 * @param value - The value to debounce
 * @param delay - The delay in milliseconds (default: 300ms)
 * @returns The debounced value
 *
 * @example
 * ```tsx
 * const [searchQuery, setSearchQuery] = useState("");
 * const debouncedSearch = useDebounce(searchQuery, 300);
 *
 * // Use debouncedSearch in your query
 * const { data } = useQuery({
 *   queryKey: ["search", debouncedSearch],
 *   queryFn: () => api.search(debouncedSearch),
 * });
 * ```
 */
export function useDebounce<T>(value: T, delay = 300): T {
	const [debouncedValue, setDebouncedValue] = useState<T>(value);

	useEffect(() => {
		// Set up a timer to update the debounced value
		const timer = setTimeout(() => {
			setDebouncedValue(value);
		}, delay);

		// Cleanup: clear the timer if value changes before delay expires
		return () => {
			clearTimeout(timer);
		};
	}, [value, delay]);

	return debouncedValue;
}

/**
 * Debounces a callback function.
 *
 * @param callback - The callback to debounce
 * @param delay - The delay in milliseconds (default: 300ms)
 * @returns A debounced version of the callback
 *
 * @example
 * ```tsx
 * const debouncedSearch = useDebouncedCallback(
 *   (query: string) => api.search(query),
 *   300
 * );
 * ```
 */
export function useDebouncedCallback<T extends (...args: Parameters<T>) => ReturnType<T>>(
	callback: T,
	delay = 300,
): (...args: Parameters<T>) => void {
	const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const callbackRef = useRef(callback);

	// Keep callback ref up to date
	useEffect(() => {
		callbackRef.current = callback;
	}, [callback]);

	useEffect(() => {
		// Cleanup on unmount
		return () => {
			if (timeoutRef.current) {
				clearTimeout(timeoutRef.current);
				timeoutRef.current = null;
			}
		};
	}, []);

	return (...args: Parameters<T>) => {
		if (timeoutRef.current) {
			clearTimeout(timeoutRef.current);
		}

		timeoutRef.current = setTimeout(() => {
			callbackRef.current(...args);
		}, delay);
	};
}

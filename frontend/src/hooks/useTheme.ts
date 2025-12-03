/**
 * Theme hook for dark mode support.
 */

import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark" | "system";

const THEME_KEY = "async-task-q-monitor-theme";

/**
 * Get the system color scheme preference.
 */
function getSystemTheme(): "light" | "dark" {
	if (typeof window === "undefined") return "light";
	return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * Get the stored theme preference.
 */
function getStoredTheme(): Theme {
	if (typeof window === "undefined") return "system";
	const stored = localStorage.getItem(THEME_KEY);
	if (stored === "light" || stored === "dark" || stored === "system") {
		return stored;
	}
	return "system";
}

/**
 * Apply theme to document.
 */
function applyTheme(theme: "light" | "dark"): void {
	const root = document.documentElement;
	if (theme === "dark") {
		root.classList.add("dark");
	} else {
		root.classList.remove("dark");
	}
}

export interface UseThemeReturn {
	/** Current resolved theme (light or dark) */
	theme: "light" | "dark";
	/** Raw theme setting (including system) */
	themeSetting: Theme;
	/** Set the theme */
	setTheme: (theme: Theme) => void;
	/** Toggle between light and dark */
	toggleTheme: () => void;
}

/**
 * Hook for managing theme state with system preference detection.
 */
export function useTheme(): UseThemeReturn {
	const [themeSetting, setThemeSetting] = useState<Theme>(() => getStoredTheme());
	const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">(() => {
		const setting = getStoredTheme();
		return setting === "system" ? getSystemTheme() : setting;
	});

	// Apply theme on mount and when setting changes
	useEffect(() => {
		const resolved = themeSetting === "system" ? getSystemTheme() : themeSetting;
		setResolvedTheme(resolved);
		applyTheme(resolved);
		localStorage.setItem(THEME_KEY, themeSetting);
	}, [themeSetting]);

	// Listen for system theme changes
	useEffect(() => {
		if (themeSetting !== "system") return;

		const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

		const handleChange = (e: MediaQueryListEvent) => {
			const newTheme = e.matches ? "dark" : "light";
			setResolvedTheme(newTheme);
			applyTheme(newTheme);
		};

		mediaQuery.addEventListener("change", handleChange);
		return () => mediaQuery.removeEventListener("change", handleChange);
	}, [themeSetting]);

	const setTheme = useCallback((theme: Theme) => {
		setThemeSetting(theme);
	}, []);

	const toggleTheme = useCallback(() => {
		setThemeSetting((current) => {
			if (current === "system") {
				return getSystemTheme() === "dark" ? "light" : "dark";
			}
			return current === "dark" ? "light" : "dark";
		});
	}, []);

	return {
		theme: resolvedTheme,
		themeSetting,
		setTheme,
		toggleTheme,
	};
}

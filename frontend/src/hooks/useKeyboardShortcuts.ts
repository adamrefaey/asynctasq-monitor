/**
 * Keyboard shortcuts hook for navigation and actions.
 * Supports single keys and key sequences (e.g., 'g d' for Go to Dashboard).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * Shortcut definition.
 */
export interface Shortcut {
	/** Keys to trigger the shortcut (e.g., '?' or 'g d') */
	keys: string;
	/** Human-readable description */
	description: string;
	/** Category for grouping in help modal */
	category: "navigation" | "actions" | "modal" | "general";
	/** Handler function */
	handler: () => void;
}

/**
 * Keyboard shortcuts grouped by category.
 */
export interface ShortcutsByCategory {
	navigation: Shortcut[];
	actions: Shortcut[];
	modal: Shortcut[];
	general: Shortcut[];
}

/**
 * Options for the keyboard shortcuts hook.
 */
interface UseKeyboardShortcutsOptions {
	/** Whether shortcuts are enabled */
	enabled?: boolean;
	/** Callback when help modal should be shown */
	onShowHelp?: () => void;
}

/**
 * Return type for the keyboard shortcuts hook.
 */
interface UseKeyboardShortcutsReturn {
	/** All registered shortcuts */
	shortcuts: Shortcut[];
	/** Shortcuts grouped by category */
	shortcutsByCategory: ShortcutsByCategory;
	/** Current key sequence being typed */
	currentSequence: string;
	/** Register a custom shortcut */
	registerShortcut: (shortcut: Shortcut) => void;
	/** Unregister a shortcut by keys */
	unregisterShortcut: (keys: string) => void;
}

/**
 * Check if the event target is an input element.
 */
function isInputElement(target: EventTarget | null): boolean {
	if (!target) return false;
	const element = target as HTMLElement;
	const tagName = element.tagName?.toLowerCase();
	return (
		tagName === "input" ||
		tagName === "textarea" ||
		tagName === "select" ||
		element.isContentEditable
	);
}

/**
 * Parse a key string into a normalized format.
 */
function normalizeKey(event: KeyboardEvent): string {
	// Handle special keys
	if (event.key === " ") return "Space";
	if (event.key === "?") return "?";
	if (event.key === "/") return "/";
	if (event.key === "Escape") return "Escape";

	// Return lowercase for letters
	return event.key.toLowerCase();
}

/**
 * Hook for managing keyboard shortcuts with sequence support.
 */
export function useKeyboardShortcuts(
	options: UseKeyboardShortcutsOptions = {},
): UseKeyboardShortcutsReturn {
	const { enabled = true, onShowHelp } = options;
	const navigate = useNavigate();

	// State for key sequence tracking
	const [currentSequence, setCurrentSequence] = useState("");
	const sequenceTimeoutRef = useRef<number | null>(null);
	const customShortcutsRef = useRef<Shortcut[]>([]);

	// Clear sequence after timeout
	const clearSequence = useCallback(() => {
		setCurrentSequence("");
		if (sequenceTimeoutRef.current) {
			window.clearTimeout(sequenceTimeoutRef.current);
			sequenceTimeoutRef.current = null;
		}
	}, []);

	// Default navigation shortcuts - memoized to prevent recreation on every render
	const shortcuts = useMemo<Shortcut[]>(
		() => [
			// Navigation (g + key sequences)
			{
				keys: "g d",
				description: "Go to Dashboard",
				category: "navigation",
				handler: () => navigate("/"),
			},
			{
				keys: "g t",
				description: "Go to Tasks",
				category: "navigation",
				handler: () => navigate("/tasks"),
			},
			{
				keys: "g w",
				description: "Go to Workers",
				category: "navigation",
				handler: () => navigate("/workers"),
			},
			{
				keys: "g q",
				description: "Go to Queues",
				category: "navigation",
				handler: () => navigate("/queues"),
			},
			{
				keys: "g s",
				description: "Go to Settings",
				category: "navigation",
				handler: () => navigate("/settings"),
			},

			// General shortcuts
			{
				keys: "?",
				description: "Show keyboard shortcuts",
				category: "general",
				handler: () => onShowHelp?.(),
			},
			{
				keys: "Escape",
				description: "Close modal / Clear selection",
				category: "general",
				handler: () => {
					// Escape is typically handled by modals themselves
				},
			},

			// Action shortcuts
			{
				keys: "r",
				description: "Refresh current view",
				category: "actions",
				handler: () => {
					// Trigger a refetch - this will be handled by the page
					window.dispatchEvent(new CustomEvent("keyboard-refresh"));
				},
			},
			{
				keys: "/",
				description: "Focus search",
				category: "actions",
				handler: () => {
					// Focus the search input if it exists
					const searchInput = document.querySelector<HTMLInputElement>(
						'input[type="search"], input[placeholder*="Search"]',
					);
					searchInput?.focus();
				},
			},
			// Include custom shortcuts
			...customShortcutsRef.current,
		],
		[navigate, onShowHelp],
	);

	// Group shortcuts by category
	const shortcutsByCategory = useMemo<ShortcutsByCategory>(
		() => ({
			navigation: shortcuts.filter((s) => s.category === "navigation"),
			actions: shortcuts.filter((s) => s.category === "actions"),
			modal: shortcuts.filter((s) => s.category === "modal"),
			general: shortcuts.filter((s) => s.category === "general"),
		}),
		[shortcuts],
	);

	// Handle keydown events
	useEffect(() => {
		if (!enabled) return;

		const handleKeyDown = (event: KeyboardEvent) => {
			// Skip if typing in an input
			if (isInputElement(event.target)) return;

			// Skip if modifier keys are pressed (except shift for '?')
			if (event.ctrlKey || event.altKey || event.metaKey) return;

			const key = normalizeKey(event);

			// Build the current sequence
			const newSequence = currentSequence ? `${currentSequence} ${key}` : key;

			// Clear previous timeout
			if (sequenceTimeoutRef.current) {
				window.clearTimeout(sequenceTimeoutRef.current);
			}

			// Check for exact match
			const matchedShortcut = shortcuts.find((s) => s.keys === newSequence);

			if (matchedShortcut) {
				event.preventDefault();
				matchedShortcut.handler();
				clearSequence();
				return;
			}

			// Check if this could be a prefix of a sequence
			const isPotentialSequence = shortcuts.some((s) => s.keys.startsWith(newSequence));

			if (isPotentialSequence) {
				setCurrentSequence(newSequence);
				// Set timeout to clear sequence after 1 second
				sequenceTimeoutRef.current = window.setTimeout(clearSequence, 1000);
			} else {
				clearSequence();
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => {
			window.removeEventListener("keydown", handleKeyDown);
			if (sequenceTimeoutRef.current) {
				window.clearTimeout(sequenceTimeoutRef.current);
			}
		};
	}, [enabled, currentSequence, shortcuts, clearSequence]);

	// Register a custom shortcut
	const registerShortcut = useCallback((shortcut: Shortcut) => {
		customShortcutsRef.current = [...customShortcutsRef.current, shortcut];
	}, []);

	// Unregister a shortcut
	const unregisterShortcut = useCallback((keys: string) => {
		customShortcutsRef.current = customShortcutsRef.current.filter((s) => s.keys !== keys);
	}, []);

	return {
		shortcuts,
		shortcutsByCategory,
		currentSequence,
		registerShortcut,
		unregisterShortcut,
	};
}

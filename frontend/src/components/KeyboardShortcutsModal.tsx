/**
 * Keyboard shortcuts help modal component.
 * Displays all available keyboard shortcuts grouped by category.
 */

import { Keyboard } from "lucide-react";
import { Button, Modal, ModalDialog } from "@/components/ui";
import type { ShortcutsByCategory } from "@/hooks/useKeyboardShortcuts";

interface KeyboardShortcutsModalProps {
	/** Whether the modal is open */
	isOpen: boolean;
	/** Callback to close the modal */
	onClose: () => void;
	/** Shortcuts grouped by category */
	shortcuts: ShortcutsByCategory;
}

/**
 * Render a keyboard key badge.
 */
function KeyBadge({ children }: { children: string }): React.ReactNode {
	return (
		<kbd className="inline-flex h-6 min-w-6 items-center justify-center rounded border border-zinc-300 bg-zinc-100 px-1.5 font-mono text-xs font-medium text-zinc-700 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
			{children}
		</kbd>
	);
}

/**
 * Render a key sequence (e.g., "g d" -> <Key>g</Key> then <Key>d</Key>).
 */
function KeySequence({ keys }: { keys: string }): React.ReactNode {
	const parts = keys.split(" ");

	return (
		<span className="inline-flex items-center gap-1">
			{parts.map((key, index) => (
				<span key={key} className="inline-flex items-center gap-1">
					<KeyBadge>{key}</KeyBadge>
					{index < parts.length - 1 && (
						<span className="text-xs text-zinc-400 dark:text-zinc-500">then</span>
					)}
				</span>
			))}
		</span>
	);
}

/**
 * Category section component.
 */
function ShortcutCategory({
	title,
	shortcuts,
}: {
	title: string;
	shortcuts: { keys: string; description: string }[];
}): React.ReactNode {
	if (shortcuts.length === 0) return null;

	return (
		<div className="space-y-2">
			<h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{title}</h3>
			<div className="space-y-1.5">
				{shortcuts.map((shortcut) => (
					<div
						key={shortcut.keys}
						className="flex items-center justify-between rounded-lg bg-zinc-50 px-3 py-2 dark:bg-zinc-800/50"
					>
						<span className="text-sm text-zinc-600 dark:text-zinc-400">{shortcut.description}</span>
						<KeySequence keys={shortcut.keys} />
					</div>
				))}
			</div>
		</div>
	);
}

/**
 * Keyboard shortcuts help modal.
 */
export function KeyboardShortcutsModal({
	isOpen,
	onClose,
	shortcuts,
}: KeyboardShortcutsModalProps): React.ReactNode {
	return (
		<Modal isOpen={isOpen} onOpenChange={(open) => !open && onClose()} size="lg">
			<ModalDialog title="Keyboard Shortcuts">
				<Modal.Body>
					<div className="space-y-6">
						{/* Navigation shortcuts */}
						<ShortcutCategory
							title="Navigation"
							shortcuts={shortcuts.navigation.map((s) => ({
								keys: s.keys,
								description: s.description,
							}))}
						/>

						{/* Action shortcuts */}
						<ShortcutCategory
							title="Actions"
							shortcuts={shortcuts.actions.map((s) => ({
								keys: s.keys,
								description: s.description,
							}))}
						/>

						{/* General shortcuts */}
						<ShortcutCategory
							title="General"
							shortcuts={shortcuts.general.map((s) => ({
								keys: s.keys,
								description: s.description,
							}))}
						/>

						{/* Modal shortcuts */}
						{shortcuts.modal.length > 0 && (
							<ShortcutCategory
								title="Modal"
								shortcuts={shortcuts.modal.map((s) => ({
									keys: s.keys,
									description: s.description,
								}))}
							/>
						)}
					</div>

					{/* Hint text */}
					<div className="mt-6 flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-300">
						<Keyboard className="h-4 w-4 shrink-0" />
						<span>
							Press <KeyBadge>?</KeyBadge> anytime to show this help
						</span>
					</div>
				</Modal.Body>

				<Modal.Footer>
					<Button variant="outline" onPress={onClose}>
						Close
					</Button>
				</Modal.Footer>
			</ModalDialog>
		</Modal>
	);
}

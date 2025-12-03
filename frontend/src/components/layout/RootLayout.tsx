/**
 * Root layout component with sidebar, header, and main content area.
 */

import { useState } from "react";
import { Outlet } from "react-router-dom";
import { KeyboardShortcutsModal } from "@/components/KeyboardShortcutsModal";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function RootLayout(): React.ReactNode {
	// Global WebSocket connection for real-time updates
	const { isConnected } = useWebSocket({
		room: "global",
		autoConnect: true,
	});

	// Keyboard shortcuts modal state
	const [showShortcutsModal, setShowShortcutsModal] = useState(false);

	// Initialize keyboard shortcuts
	const { shortcutsByCategory, currentSequence } = useKeyboardShortcuts({
		enabled: true,
		onShowHelp: () => setShowShortcutsModal(true),
	});

	return (
		<div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
			{/* Sidebar */}
			<Sidebar />

			{/* Main content area */}
			<div className="pl-64">
				<Header isConnected={isConnected} />

				{/* Page content */}
				<main className="min-h-[calc(100vh-4rem)] p-6">
					<Outlet />
				</main>
			</div>

			{/* Key sequence indicator */}
			{currentSequence && (
				<div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50">
					<div className="flex items-center gap-1 rounded-lg bg-zinc-900 px-3 py-2 text-sm text-white shadow-lg dark:bg-zinc-800">
						<span className="text-zinc-400">Keys:</span>
						<kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded border border-zinc-600 bg-zinc-700 px-1.5 font-mono text-xs">
							{currentSequence}
						</kbd>
					</div>
				</div>
			)}

			{/* Keyboard shortcuts modal */}
			<KeyboardShortcutsModal
				isOpen={showShortcutsModal}
				onClose={() => setShowShortcutsModal(false)}
				shortcuts={shortcutsByCategory}
			/>
		</div>
	);
}

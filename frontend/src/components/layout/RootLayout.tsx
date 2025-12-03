/**
 * Root layout component with sidebar, header, and main content area.
 */

import { Outlet } from "react-router-dom";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function RootLayout(): React.ReactNode {
	// Global WebSocket connection for real-time updates
	const { isConnected } = useWebSocket({
		room: "global",
		autoConnect: true,
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
		</div>
	);
}

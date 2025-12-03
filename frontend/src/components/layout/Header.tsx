/**
 * Header component with search and user actions.
 */

import { Bell, Moon, Search, Sun, Wifi, WifiOff } from "lucide-react";
import { useState } from "react";
import { useLocation } from "react-router-dom";
import { Button } from "@/components/ui";
import { useTheme } from "@/hooks/useTheme";

interface HeaderProps {
	isConnected?: boolean;
}

const pageTitle: Record<string, string> = {
	"/": "Dashboard",
	"/tasks": "Tasks",
	"/workers": "Workers",
	"/queues": "Queues",
	"/metrics": "Metrics",
	"/settings": "Settings",
};

export function Header({ isConnected = false }: HeaderProps): React.ReactNode {
	const location = useLocation();
	const { theme, toggleTheme } = useTheme();
	const [searchQuery, setSearchQuery] = useState("");

	const title = pageTitle[location.pathname] ?? "Not Found";

	return (
		<header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-zinc-200 bg-white/80 px-6 backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-900/80">
			{/* Page title */}
			<h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">{title}</h1>

			{/* Right section */}
			<div className="flex items-center gap-4">
				{/* Search */}
				<div className="relative w-64">
					<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
					<input
						type="search"
						placeholder="Search tasks..."
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						className="h-9 w-full rounded-lg border border-zinc-300 bg-white pl-9 pr-3 text-sm outline-none placeholder:text-zinc-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
					/>
				</div>

				{/* Connection status */}
				<div
					className="flex items-center gap-1.5"
					title={isConnected ? "Connected" : "Disconnected"}
				>
					{isConnected ? (
						<Wifi className="h-4 w-4 text-emerald-500" />
					) : (
						<WifiOff className="h-4 w-4 text-red-500" />
					)}
					<span
						className={`text-xs font-medium ${isConnected ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}
					>
						{isConnected ? "Live" : "Offline"}
					</span>
				</div>

				{/* Theme toggle */}
				<Button
					variant="ghost"
					size="icon-sm"
					onPress={toggleTheme}
					aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
				>
					{theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
				</Button>

				{/* Notifications */}
				<Button variant="ghost" size="icon-sm" aria-label="Notifications">
					<Bell className="h-4 w-4" />
				</Button>
			</div>
		</header>
	);
}

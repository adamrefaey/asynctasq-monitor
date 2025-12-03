/**
 * Sidebar navigation component.
 */

import {
	BarChart3,
	Layers,
	LayoutDashboard,
	ListTodo,
	type LucideIcon,
	Settings,
	Users,
} from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import { tv } from "tailwind-variants";

interface NavItem {
	name: string;
	href: string;
	icon: LucideIcon;
}

const navItems: NavItem[] = [
	{ name: "Dashboard", href: "/", icon: LayoutDashboard },
	{ name: "Tasks", href: "/tasks", icon: ListTodo },
	{ name: "Workers", href: "/workers", icon: Users },
	{ name: "Queues", href: "/queues", icon: Layers },
	{ name: "Metrics", href: "/metrics", icon: BarChart3 },
	{ name: "Settings", href: "/settings", icon: Settings },
];

const navLinkStyles = tv({
	base: [
		"flex items-center gap-3 px-3 py-2 rounded-lg",
		"text-sm font-medium transition-colors",
		"outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
	],
	variants: {
		active: {
			true: ["bg-blue-50 text-blue-700", "dark:bg-blue-900/30 dark:text-blue-400"],
			false: [
				"text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900",
				"dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100",
			],
		},
	},
	defaultVariants: {
		active: false,
	},
});

export function Sidebar(): React.ReactNode {
	const location = useLocation();

	return (
		<aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
			{/* Logo */}
			<div className="flex h-16 items-center gap-3 border-b border-zinc-200 px-6 dark:border-zinc-800">
				<div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
					<span className="text-sm font-bold text-white">Q</span>
				</div>
				<span className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">Task Monitor</span>
			</div>

			{/* Navigation */}
			<nav className="flex flex-col gap-1 p-4">
				{navItems.map((item) => {
					const isActive =
						item.href === "/" ? location.pathname === "/" : location.pathname.startsWith(item.href);

					return (
						<NavLink key={item.href} to={item.href} className={navLinkStyles({ active: isActive })}>
							<item.icon className="h-5 w-5" aria-hidden="true" />
							{item.name}
						</NavLink>
					);
				})}
			</nav>

			{/* Footer */}
			<div className="absolute bottom-0 left-0 right-0 border-t border-zinc-200 p-4 dark:border-zinc-800">
				<div className="text-xs text-zinc-500 dark:text-zinc-400">
					async-task-q-monitor
					<br />
					<span className="font-medium">v1.0.0</span>
				</div>
			</div>
		</aside>
	);
}

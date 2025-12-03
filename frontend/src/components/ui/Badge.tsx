/**
 * Badge component for displaying status indicators.
 */

import { tv, type VariantProps } from "tailwind-variants";

const badgeStyles = tv({
	base: [
		"inline-flex items-center gap-1.5",
		"rounded-full px-2.5 py-0.5",
		"text-xs font-medium",
		"ring-1 ring-inset",
	],
	variants: {
		variant: {
			default: [
				"bg-zinc-100 text-zinc-700 ring-zinc-200",
				"dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-700",
			],
			success: [
				"bg-emerald-50 text-emerald-700 ring-emerald-200",
				"dark:bg-emerald-900/30 dark:text-emerald-400 dark:ring-emerald-800",
			],
			warning: [
				"bg-amber-50 text-amber-700 ring-amber-200",
				"dark:bg-amber-900/30 dark:text-amber-400 dark:ring-amber-800",
			],
			error: [
				"bg-red-50 text-red-700 ring-red-200",
				"dark:bg-red-900/30 dark:text-red-400 dark:ring-red-800",
			],
			info: [
				"bg-blue-50 text-blue-700 ring-blue-200",
				"dark:bg-blue-900/30 dark:text-blue-400 dark:ring-blue-800",
			],
			pending: [
				"bg-yellow-50 text-yellow-700 ring-yellow-200",
				"dark:bg-yellow-900/30 dark:text-yellow-400 dark:ring-yellow-800",
			],
			running: [
				"bg-cyan-50 text-cyan-700 ring-cyan-200",
				"dark:bg-cyan-900/30 dark:text-cyan-400 dark:ring-cyan-800",
			],
		},
		size: {
			sm: "text-[10px] px-1.5 py-0.5",
			md: "text-xs px-2.5 py-0.5",
			lg: "text-sm px-3 py-1",
		},
	},
	defaultVariants: {
		variant: "default",
		size: "md",
	},
});

export type BadgeVariant = NonNullable<VariantProps<typeof badgeStyles>["variant"]>;

export interface BadgeProps extends VariantProps<typeof badgeStyles> {
	children: React.ReactNode;
	className?: string;
	/** Optional dot indicator */
	dot?: boolean;
}

/**
 * Badge component for status indicators.
 */
export function Badge({
	children,
	className,
	variant,
	size,
	dot = false,
}: BadgeProps): React.ReactNode {
	return (
		<span className={badgeStyles({ variant, size, className })}>
			{dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />}
			{children}
		</span>
	);
}

/**
 * Get badge variant based on task status.
 */
export function getTaskStatusBadgeVariant(status: string): BadgeVariant {
	const statusMap: Record<string, BadgeVariant> = {
		pending: "pending",
		running: "running",
		completed: "success",
		failed: "error",
		retrying: "warning",
		cancelled: "default",
	};

	return statusMap[status] ?? "default";
}

/**
 * Get badge variant based on worker status.
 */
export function getWorkerStatusBadgeVariant(status: string): BadgeVariant {
	const statusMap: Record<string, BadgeVariant> = {
		active: "success",
		idle: "info",
		down: "error",
	};

	return statusMap[status] ?? "default";
}

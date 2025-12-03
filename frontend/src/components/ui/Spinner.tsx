/**
 * Spinner component for loading states.
 */

import { tv, type VariantProps } from "tailwind-variants";

const spinnerStyles = tv({
	base: "animate-spin",
	variants: {
		size: {
			sm: "h-4 w-4",
			md: "h-6 w-6",
			lg: "h-8 w-8",
			xl: "h-12 w-12",
		},
		color: {
			default: "text-zinc-400",
			primary: "text-blue-600",
			white: "text-white",
			current: "text-current",
		},
	},
	defaultVariants: {
		size: "md",
		color: "primary",
	},
});

export interface SpinnerProps extends VariantProps<typeof spinnerStyles> {
	className?: string;
	label?: string;
}

export function Spinner({
	className,
	size,
	color,
	label = "Loading...",
}: SpinnerProps): React.ReactNode {
	return (
		<svg
			className={spinnerStyles({ size, color, className })}
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			role="img"
			aria-label={label}
		>
			<title>{label}</title>
			<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
			<path
				className="opacity-75"
				fill="currentColor"
				d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
			/>
		</svg>
	);
}

export interface LoadingOverlayProps {
	children?: React.ReactNode;
	label?: string;
}

export function LoadingOverlay({
	children,
	label = "Loading...",
}: LoadingOverlayProps): React.ReactNode {
	return (
		<div className="flex flex-col items-center justify-center gap-3 p-8">
			<Spinner size="lg" />
			{children ?? <p className="text-sm text-zinc-500 dark:text-zinc-400">{label}</p>}
		</div>
	);
}

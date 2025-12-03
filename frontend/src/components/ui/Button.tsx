/**
 * Button component built with React Aria Components.
 * Provides accessible, styleable button with multiple variants.
 */

import {
	Button as AriaButton,
	type ButtonProps as AriaButtonProps,
	composeRenderProps,
} from "react-aria-components";
import { tv, type VariantProps } from "tailwind-variants";

/**
 * Button style variants using tailwind-variants.
 */
const buttonStyles = tv({
	base: [
		"inline-flex items-center justify-center gap-2",
		"rounded-lg font-medium text-sm",
		"transition-colors duration-150",
		"outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
		"disabled:opacity-50 disabled:cursor-not-allowed",
		"cursor-default select-none",
	],
	variants: {
		variant: {
			primary: [
				"bg-blue-600 text-white",
				"hover:bg-blue-700",
				"data-[pressed]:bg-blue-800",
				"focus-visible:ring-blue-500",
			],
			secondary: [
				"bg-zinc-100 text-zinc-900",
				"hover:bg-zinc-200",
				"data-[pressed]:bg-zinc-300",
				"focus-visible:ring-zinc-400",
				"dark:bg-zinc-800 dark:text-zinc-100",
				"dark:hover:bg-zinc-700",
				"dark:data-[pressed]:bg-zinc-600",
			],
			outline: [
				"border border-zinc-300 bg-transparent text-zinc-900",
				"hover:bg-zinc-100",
				"data-[pressed]:bg-zinc-200",
				"focus-visible:ring-zinc-400",
				"dark:border-zinc-600 dark:text-zinc-100",
				"dark:hover:bg-zinc-800",
				"dark:data-[pressed]:bg-zinc-700",
			],
			ghost: [
				"bg-transparent text-zinc-900",
				"hover:bg-zinc-100",
				"data-[pressed]:bg-zinc-200",
				"focus-visible:ring-zinc-400",
				"dark:text-zinc-100",
				"dark:hover:bg-zinc-800",
				"dark:data-[pressed]:bg-zinc-700",
			],
			danger: [
				"bg-red-600 text-white",
				"hover:bg-red-700",
				"data-[pressed]:bg-red-800",
				"focus-visible:ring-red-500",
			],
			success: [
				"bg-emerald-600 text-white",
				"hover:bg-emerald-700",
				"data-[pressed]:bg-emerald-800",
				"focus-visible:ring-emerald-500",
			],
		},
		size: {
			sm: "h-8 px-3 text-xs",
			md: "h-10 px-4 text-sm",
			lg: "h-12 px-6 text-base",
			icon: "h-10 w-10 p-0",
			"icon-sm": "h-8 w-8 p-0",
		},
	},
	defaultVariants: {
		variant: "primary",
		size: "md",
	},
});

export type ButtonVariant = NonNullable<VariantProps<typeof buttonStyles>["variant"]>;
export type ButtonSize = NonNullable<VariantProps<typeof buttonStyles>["size"]>;

export interface ButtonProps
	extends Omit<AriaButtonProps, "className">,
		VariantProps<typeof buttonStyles> {
	className?: string;
}

/**
 * Accessible button component with multiple variants and sizes.
 */
export function Button({ className, variant, size, ...props }: ButtonProps): React.ReactNode {
	return (
		<AriaButton
			{...props}
			className={composeRenderProps(className, (className) =>
				buttonStyles({ variant, size, className }),
			)}
		/>
	);
}

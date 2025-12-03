/**
 * Card component for dashboard and content sections.
 */

import { tv, type VariantProps } from "tailwind-variants";

const cardStyles = tv({
	slots: {
		root: ["rounded-xl border bg-white", "dark:bg-zinc-900 dark:border-zinc-800"],
		header: [
			"flex items-center justify-between gap-4",
			"border-b px-6 py-4",
			"dark:border-zinc-800",
		],
		title: "text-lg font-semibold text-zinc-900 dark:text-zinc-100",
		description: "text-sm text-zinc-500 dark:text-zinc-400",
		content: "p-6",
		footer: ["flex items-center justify-end gap-3", "border-t px-6 py-4", "dark:border-zinc-800"],
	},
	variants: {
		variant: {
			default: {
				root: "border-zinc-200",
			},
			elevated: {
				root: "border-transparent shadow-lg",
			},
			outline: {
				root: "border-zinc-300 dark:border-zinc-700",
			},
		},
		padding: {
			none: {
				content: "p-0",
			},
			sm: {
				content: "p-4",
			},
			md: {
				content: "p-6",
			},
			lg: {
				content: "p-8",
			},
		},
	},
	defaultVariants: {
		variant: "default",
		padding: "md",
	},
});

type CardStylesVariants = VariantProps<typeof cardStyles>;

export interface CardProps extends CardStylesVariants {
	children: React.ReactNode;
	className?: string;
}

export interface CardHeaderProps {
	children: React.ReactNode;
	className?: string;
}

export interface CardTitleProps {
	children: React.ReactNode;
	className?: string;
	as?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
}

export interface CardDescriptionProps {
	children: React.ReactNode;
	className?: string;
}

export interface CardContentProps {
	children: React.ReactNode;
	className?: string;
}

export interface CardFooterProps {
	children: React.ReactNode;
	className?: string;
}

const { header, title, description, content, footer } = cardStyles();

function CardRoot({ children, className, variant, padding }: CardProps): React.ReactNode {
	const styles = cardStyles({ variant, padding });
	return <div className={styles.root({ className })}>{children}</div>;
}

function CardHeaderComponent({ children, className }: CardHeaderProps): React.ReactNode {
	return <div className={header({ className })}>{children}</div>;
}

function CardTitleComponent({
	children,
	className,
	as: Component = "h3",
}: CardTitleProps): React.ReactNode {
	return <Component className={title({ className })}>{children}</Component>;
}

function CardDescriptionComponent({ children, className }: CardDescriptionProps): React.ReactNode {
	return <p className={description({ className })}>{children}</p>;
}

function CardContentComponent({ children, className }: CardContentProps): React.ReactNode {
	return <div className={content({ className })}>{children}</div>;
}

function CardFooterComponent({ children, className }: CardFooterProps): React.ReactNode {
	return <div className={footer({ className })}>{children}</div>;
}

// Compound component pattern
export const Card = Object.assign(CardRoot, {
	Header: CardHeaderComponent,
	Title: CardTitleComponent,
	Description: CardDescriptionComponent,
	Content: CardContentComponent,
	Footer: CardFooterComponent,
});

// Also export individual components for flexibility
export const CardHeader = CardHeaderComponent;
export const CardTitle = CardTitleComponent;
export const CardDescription = CardDescriptionComponent;
export const CardContent = CardContentComponent;
export const CardFooter = CardFooterComponent;

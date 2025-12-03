/**
 * Modal and Dialog components built with React Aria Components.
 */

import { X } from "lucide-react";
import {
	Modal as AriaModal,
	Dialog,
	type DialogProps,
	DialogTrigger,
	Heading,
	ModalOverlay,
	type ModalOverlayProps,
} from "react-aria-components";
import { tv, type VariantProps } from "tailwind-variants";
import { Button } from "./Button";

const modalStyles = tv({
	slots: {
		overlay: [
			"fixed inset-0 z-50 bg-black/50 backdrop-blur-sm",
			"flex items-center justify-center p-4",
			"entering:animate-in entering:fade-in entering:duration-200",
			"exiting:animate-out exiting:fade-out exiting:duration-150",
		],
		modal: [
			"w-full max-h-[90vh] overflow-hidden rounded-xl bg-white shadow-2xl",
			"dark:bg-zinc-900 dark:border dark:border-zinc-800",
			"entering:animate-in entering:fade-in entering:zoom-in-95 entering:duration-200",
			"exiting:animate-out exiting:fade-out exiting:zoom-out-95 exiting:duration-150",
		],
		dialog: "outline-none",
		header: [
			"flex items-center justify-between gap-4 px-6 py-4",
			"border-b border-zinc-200 dark:border-zinc-800",
		],
		title: "text-lg font-semibold text-zinc-900 dark:text-zinc-100",
		closeButton: [
			"rounded-lg p-2 text-zinc-400",
			"hover:bg-zinc-100 hover:text-zinc-600",
			"dark:hover:bg-zinc-800 dark:hover:text-zinc-300",
		],
		content: "overflow-auto",
		footer: [
			"flex items-center justify-end gap-3 px-6 py-4",
			"border-t border-zinc-200 dark:border-zinc-800",
		],
	},
	variants: {
		size: {
			sm: {
				modal: "max-w-sm",
			},
			md: {
				modal: "max-w-md",
			},
			lg: {
				modal: "max-w-lg",
			},
			xl: {
				modal: "max-w-xl",
			},
			"2xl": {
				modal: "max-w-2xl",
			},
			full: {
				modal: "max-w-[calc(100vw-2rem)]",
			},
		},
	},
	defaultVariants: {
		size: "md",
	},
});

type ModalStylesVariants = VariantProps<typeof modalStyles>;

export interface ModalProps extends ModalOverlayProps, ModalStylesVariants {
	children: React.ReactNode;
}

function ModalRoot({ children, size, ...props }: ModalProps): React.ReactNode {
	const styles = modalStyles({ size });

	return (
		<ModalOverlay {...props} className={styles.overlay()}>
			<AriaModal className={styles.modal()}>{children}</AriaModal>
		</ModalOverlay>
	);
}

export interface ModalDialogProps extends Omit<DialogProps, "className"> {
	title: string;
	children: React.ReactNode;
	className?: string;
	/** Whether to show close button in header */
	showCloseButton?: boolean;
}

export function ModalDialog({
	title,
	children,
	className,
	showCloseButton = true,
	...props
}: ModalDialogProps): React.ReactNode {
	const styles = modalStyles();

	return (
		<Dialog {...props} className={styles.dialog({ className })}>
			{({ close }) => (
				<>
					<div className={styles.header()}>
						<Heading slot="title" className={styles.title()}>
							{title}
						</Heading>
						{showCloseButton && (
							<Button
								variant="ghost"
								size="icon-sm"
								onPress={close}
								aria-label="Close dialog"
								className={styles.closeButton()}
							>
								<X className="h-4 w-4" />
							</Button>
						)}
					</div>
					{children}
				</>
			)}
		</Dialog>
	);
}

export interface ModalHeaderProps {
	children: React.ReactNode;
	className?: string;
}

function ModalHeaderComponent({ children, className }: ModalHeaderProps): React.ReactNode {
	const styles = modalStyles();
	return <div className={styles.header({ className })}>{children}</div>;
}

export interface ModalTitleProps {
	children: React.ReactNode;
	className?: string;
}

function ModalTitleComponent({ children, className }: ModalTitleProps): React.ReactNode {
	const styles = modalStyles();
	return (
		<Heading slot="title" className={styles.title({ className })}>
			{children}
		</Heading>
	);
}

export interface ModalContentProps {
	children: React.ReactNode;
	className?: string;
}

function ModalContentComponent({ children, className }: ModalContentProps): React.ReactNode {
	const styles = modalStyles();
	return <div className={styles.content({ className })}>{children}</div>;
}

export interface ModalBodyProps {
	children: React.ReactNode;
	className?: string;
}

function ModalBodyComponent({ children, className }: ModalBodyProps): React.ReactNode {
	return <div className={`p-6 ${className ?? ""}`}>{children}</div>;
}

export interface ModalFooterProps {
	children: React.ReactNode;
	className?: string;
}

function ModalFooterComponent({ children, className }: ModalFooterProps): React.ReactNode {
	const styles = modalStyles();
	return <div className={styles.footer({ className })}>{children}</div>;
}

// Compound component pattern
export const Modal = Object.assign(ModalRoot, {
	Header: ModalHeaderComponent,
	Title: ModalTitleComponent,
	Content: ModalContentComponent,
	Body: ModalBodyComponent,
	Footer: ModalFooterComponent,
});

// Also export individual components for flexibility
export const ModalContent = ModalContentComponent;
export const ModalFooter = ModalFooterComponent;

// Re-export DialogTrigger for convenience
export { DialogTrigger };

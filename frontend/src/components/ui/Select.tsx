/**
 * Select component built with React Aria Components.
 */

import { Check, ChevronDown } from "lucide-react";
import {
	Select as AriaSelect,
	type SelectProps as AriaSelectProps,
	Button,
	Label,
	ListBox,
	ListBoxItem,
	type ListBoxItemProps,
	Popover,
	SelectValue,
} from "react-aria-components";
import { tv, type VariantProps } from "tailwind-variants";

const selectStyles = tv({
	slots: {
		root: "flex flex-col gap-1.5",
		label: "text-sm font-medium text-zinc-900 dark:text-zinc-100",
		button: [
			"flex items-center justify-between w-full rounded-lg border bg-white px-3",
			"text-sm text-zinc-900",
			"outline-none transition-colors duration-150",
			"border-zinc-300 hover:border-zinc-400",
			"focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20",
			"disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-zinc-100",
			"dark:bg-zinc-900 dark:border-zinc-700 dark:text-zinc-100",
			"dark:hover:border-zinc-600",
			"dark:focus:border-blue-400 dark:focus:ring-blue-400/20",
		],
		value: "flex-1 text-left truncate",
		icon: "ml-2 h-4 w-4 text-zinc-400 transition-transform data-[open]:rotate-180",
		popover: [
			"w-[--trigger-width] rounded-lg border bg-white shadow-lg",
			"dark:bg-zinc-900 dark:border-zinc-700",
			"entering:animate-in entering:fade-in entering:zoom-in-95",
			"exiting:animate-out exiting:fade-out exiting:zoom-out-95",
		],
		listBox: "p-1 outline-none max-h-60 overflow-auto",
		item: [
			"flex items-center gap-2 px-3 py-2 rounded-md cursor-default outline-none",
			"text-sm text-zinc-900 dark:text-zinc-100",
			"data-[focused]:bg-zinc-100 dark:data-[focused]:bg-zinc-800",
			"data-[selected]:font-medium",
		],
		itemCheck: "h-4 w-4 text-blue-600 dark:text-blue-400",
	},
	variants: {
		size: {
			sm: {
				button: "h-8 text-xs",
			},
			md: {
				button: "h-10 text-sm",
			},
			lg: {
				button: "h-12 text-base",
			},
		},
	},
	defaultVariants: {
		size: "md",
	},
});

type SelectStylesVariants = VariantProps<typeof selectStyles>;

export interface SelectOption<T = string> {
	value: T;
	label: string;
	description?: string;
}

export interface SelectProps<T extends object>
	extends Omit<AriaSelectProps<T>, "className" | "children">,
		SelectStylesVariants {
	label?: string;
	placeholder?: string;
	className?: string;
	children: React.ReactNode;
}

export function Select<T extends object>({
	label,
	placeholder,
	className,
	size,
	children,
	...props
}: SelectProps<T>): React.ReactNode {
	const styles = selectStyles({ size });

	return (
		<AriaSelect {...props} className={styles.root({ className })}>
			{label && <Label className={styles.label()}>{label}</Label>}
			<Button className={styles.button()}>
				<SelectValue className={styles.value()}>
					{({ defaultChildren, isPlaceholder }) =>
						isPlaceholder ? <span className="text-zinc-400">{placeholder}</span> : defaultChildren
					}
				</SelectValue>
				<ChevronDown className={styles.icon()} aria-hidden="true" />
			</Button>
			<Popover className={styles.popover()}>
				<ListBox className={styles.listBox()}>{children}</ListBox>
			</Popover>
		</AriaSelect>
	);
}

export interface SelectItemProps extends Omit<ListBoxItemProps, "className"> {
	className?: string;
	/** Text value for accessibility - required if children is not a string */
	textValue?: string;
}

export function SelectItem({
	className,
	children,
	textValue,
	...props
}: SelectItemProps): React.ReactNode {
	const styles = selectStyles();
	const resolvedTextValue = textValue ?? (typeof children === "string" ? children : "");

	return (
		<ListBoxItem {...props} className={styles.item({ className })} textValue={resolvedTextValue}>
			{({ isSelected }) => (
				<>
					<span className="flex-1">{typeof children === "function" ? null : children}</span>
					{isSelected && <Check className={styles.itemCheck()} />}
				</>
			)}
		</ListBoxItem>
	);
}

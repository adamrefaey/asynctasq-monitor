/**
 * Input component built with React Aria Components.
 */

import {
	Input as AriaInput,
	Label as AriaLabel,
	TextField as AriaTextField,
	type TextFieldProps as AriaTextFieldProps,
	FieldError,
	Text,
	type ValidationResult,
} from "react-aria-components";
import { tv, type VariantProps } from "tailwind-variants";

const textFieldStyles = tv({
	slots: {
		root: "flex flex-col gap-1.5",
		label: "text-sm font-medium text-zinc-900 dark:text-zinc-100",
		input: [
			"w-full rounded-lg border bg-white px-3 py-2",
			"text-sm text-zinc-900 placeholder:text-zinc-400",
			"outline-none transition-colors duration-150",
			"border-zinc-300 hover:border-zinc-400",
			"focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20",
			"disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-zinc-100",
			"data-[invalid]:border-red-500 data-[invalid]:focus:ring-red-500/20",
			"dark:bg-zinc-900 dark:border-zinc-700 dark:text-zinc-100",
			"dark:placeholder:text-zinc-500 dark:hover:border-zinc-600",
			"dark:focus:border-blue-400 dark:focus:ring-blue-400/20",
			"dark:disabled:bg-zinc-800",
		],
		description: "text-xs text-zinc-500 dark:text-zinc-400",
		error: "text-xs text-red-600 dark:text-red-400",
	},
	variants: {
		size: {
			sm: {
				input: "h-8 text-xs px-2.5",
			},
			md: {
				input: "h-10 text-sm px-3",
			},
			lg: {
				input: "h-12 text-base px-4",
			},
		},
	},
	defaultVariants: {
		size: "md",
	},
});

type TextFieldStylesVariants = VariantProps<typeof textFieldStyles>;

export interface TextFieldProps
	extends Omit<AriaTextFieldProps, "className">,
		TextFieldStylesVariants {
	label?: string;
	description?: string;
	errorMessage?: string | ((validation: ValidationResult) => string);
	placeholder?: string;
	className?: string;
}

export function TextField({
	label,
	description,
	errorMessage,
	placeholder,
	className,
	size,
	...props
}: TextFieldProps): React.ReactNode {
	const styles = textFieldStyles({ size });

	return (
		<AriaTextField {...props} className={styles.root({ className })}>
			{label && <AriaLabel className={styles.label()}>{label}</AriaLabel>}
			<AriaInput className={styles.input()} placeholder={placeholder ?? ""} />
			{description && (
				<Text slot="description" className={styles.description()}>
					{description}
				</Text>
			)}
			<FieldError className={styles.error()}>{errorMessage}</FieldError>
		</AriaTextField>
	);
}

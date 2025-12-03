/**
 * Simple logger utility for development debugging.
 * In production, these logs will be no-ops.
 */

const isDev = import.meta.env.DEV;

export const logger = {
	log: (...args: unknown[]) => {
		if (isDev) {
			// biome-ignore lint/suspicious/noConsole: Debug logging for development
			console.log(...args);
		}
	},
	warn: (...args: unknown[]) => {
		if (isDev) {
			// biome-ignore lint/suspicious/noConsole: Debug logging for development
			console.warn(...args);
		}
	},
	error: (...args: unknown[]) => {
		// Always log errors, even in production
		// biome-ignore lint/suspicious/noConsole: Error logging is necessary
		console.error(...args);
	},
};

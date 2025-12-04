/**
 * Settings store using Zustand with localStorage persistence.
 * Manages all user preferences for the monitoring dashboard.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Theme options for the application.
 */
export type ThemeSetting = "light" | "dark" | "system";

/**
 * Date format display options.
 */
export type DateFormat = "relative" | "absolute";

/**
 * Table density options for data tables.
 */
export type TableDensity = "compact" | "comfortable" | "spacious";

/**
 * Log level options for debugging.
 */
export type LogLevel = "debug" | "info" | "warn" | "error";

/**
 * Timezone settings.
 */
export type TimezoneOption =
	| "UTC"
	| "America/New_York"
	| "America/Los_Angeles"
	| "Europe/London"
	| "Asia/Tokyo"
	| "auto";

/**
 * Settings state interface.
 */
interface SettingsState {
	// General settings
	theme: ThemeSetting;
	timezone: TimezoneOption;
	dateFormat: DateFormat;
	refreshInterval: number; // in seconds

	// Display settings
	tableDensity: TableDensity;
	itemsPerPage: number;
	sidebarExpanded: boolean;

	// Connection settings
	apiUrl: string;
	wsUrl: string;
	timeout: number; // in seconds

	// Notification settings
	enableNotifications: boolean;
	notifyOnFailure: boolean;
	notifyOnComplete: boolean;
	soundEnabled: boolean;

	// Advanced settings
	debugMode: boolean;
	cacheEnabled: boolean;
	maxRetries: number;
	logLevel: LogLevel;
}

/**
 * Settings actions interface.
 */
interface SettingsActions {
	// Theme actions
	setTheme: (theme: ThemeSetting) => void;

	// General setting actions
	setTimezone: (timezone: TimezoneOption) => void;
	setDateFormat: (format: DateFormat) => void;
	setRefreshInterval: (seconds: number) => void;

	// Display setting actions
	setTableDensity: (density: TableDensity) => void;
	setItemsPerPage: (count: number) => void;
	setSidebarExpanded: (expanded: boolean) => void;
	toggleSidebar: () => void;

	// Connection setting actions
	setApiUrl: (url: string) => void;
	setWsUrl: (url: string) => void;
	setTimeout: (seconds: number) => void;

	// Notification setting actions
	setEnableNotifications: (enabled: boolean) => void;
	setNotifyOnFailure: (enabled: boolean) => void;
	setNotifyOnComplete: (enabled: boolean) => void;
	setSoundEnabled: (enabled: boolean) => void;

	// Advanced setting actions
	setDebugMode: (enabled: boolean) => void;
	setCacheEnabled: (enabled: boolean) => void;
	setMaxRetries: (count: number) => void;
	setLogLevel: (level: LogLevel) => void;

	// Bulk actions
	resetToDefaults: () => void;
	clearAllData: () => void;
}

/**
 * Complete settings store type.
 */
export type SettingsStore = SettingsState & SettingsActions;

/**
 * Default settings values.
 */
const defaultSettings: SettingsState = {
	// General
	theme: "system",
	timezone: "UTC",
	dateFormat: "relative",
	refreshInterval: 5,

	// Display
	tableDensity: "comfortable",
	itemsPerPage: 25,
	sidebarExpanded: true,

	// Connection
	apiUrl: "http://localhost:8000",
	wsUrl: "ws://localhost:8000/ws",
	timeout: 30,

	// Notifications
	enableNotifications: true,
	notifyOnFailure: true,
	notifyOnComplete: false,
	soundEnabled: false,

	// Advanced
	debugMode: false,
	cacheEnabled: true,
	maxRetries: 3,
	logLevel: "info",
};

/**
 * Settings store with localStorage persistence.
 */
export const useSettingsStore = create<SettingsStore>()(
	persist(
		(set) => ({
			...defaultSettings,

			// Theme actions
			setTheme: (theme) => set({ theme }),

			// General setting actions
			setTimezone: (timezone) => set({ timezone }),
			setDateFormat: (dateFormat) => set({ dateFormat }),
			setRefreshInterval: (refreshInterval) => set({ refreshInterval }),

			// Display setting actions
			setTableDensity: (tableDensity) => set({ tableDensity }),
			setItemsPerPage: (itemsPerPage) => set({ itemsPerPage }),
			setSidebarExpanded: (sidebarExpanded) => set({ sidebarExpanded }),
			toggleSidebar: () => set((state) => ({ sidebarExpanded: !state.sidebarExpanded })),

			// Connection setting actions
			setApiUrl: (apiUrl) => set({ apiUrl }),
			setWsUrl: (wsUrl) => set({ wsUrl }),
			setTimeout: (timeout) => set({ timeout }),

			// Notification setting actions
			setEnableNotifications: (enableNotifications) => set({ enableNotifications }),
			setNotifyOnFailure: (notifyOnFailure) => set({ notifyOnFailure }),
			setNotifyOnComplete: (notifyOnComplete) => set({ notifyOnComplete }),
			setSoundEnabled: (soundEnabled) => set({ soundEnabled }),

			// Advanced setting actions
			setDebugMode: (debugMode) => set({ debugMode }),
			setCacheEnabled: (cacheEnabled) => set({ cacheEnabled }),
			setMaxRetries: (maxRetries) => set({ maxRetries }),
			setLogLevel: (logLevel) => set({ logLevel }),

			// Bulk actions
			resetToDefaults: () => set(defaultSettings),
			clearAllData: () => {
				// Clear persisted storage and reset to defaults
				localStorage.removeItem("asynctasq-monitor-settings");
				set(defaultSettings);
			},
		}),
		{
			name: "asynctasq-monitor-settings",
			// Only persist specific fields (exclude actions)
			partialize: (state) => ({
				theme: state.theme,
				timezone: state.timezone,
				dateFormat: state.dateFormat,
				refreshInterval: state.refreshInterval,
				tableDensity: state.tableDensity,
				itemsPerPage: state.itemsPerPage,
				sidebarExpanded: state.sidebarExpanded,
				apiUrl: state.apiUrl,
				wsUrl: state.wsUrl,
				timeout: state.timeout,
				enableNotifications: state.enableNotifications,
				notifyOnFailure: state.notifyOnFailure,
				notifyOnComplete: state.notifyOnComplete,
				soundEnabled: state.soundEnabled,
				debugMode: state.debugMode,
				cacheEnabled: state.cacheEnabled,
				maxRetries: state.maxRetries,
				logLevel: state.logLevel,
			}),
		},
	),
);

/**
 * Selector hooks for common use cases.
 */
export const useThemeSetting = () => useSettingsStore((state) => state.theme);
export const useRefreshInterval = () => useSettingsStore((state) => state.refreshInterval);
export const useTableDensity = () => useSettingsStore((state) => state.tableDensity);
export const useItemsPerPage = () => useSettingsStore((state) => state.itemsPerPage);
export const useDateFormatSetting = () => useSettingsStore((state) => state.dateFormat);
export const useTimezone = () => useSettingsStore((state) => state.timezone);

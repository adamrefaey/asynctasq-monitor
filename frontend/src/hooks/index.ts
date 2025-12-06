/**
 * Central export for all React Query hooks.
 */

// Dashboard hooks
export {
	dashboardKeys,
	useDashboardSummary,
	useInvalidateDashboard,
	usePrefetchQueue,
	usePrefetchWorker as usePrefetchWorkerDashboard,
	useQueue,
	useQueues,
	useWorker as useWorkerDashboard,
	useWorkers as useWorkersDashboard,
} from "./useDashboard";

// Debounce hooks
export { useDebounce, useDebouncedCallback } from "./useDebounce";

// Keyboard shortcuts hook
export {
	type Shortcut,
	type ShortcutsByCategory,
	useKeyboardShortcuts,
} from "./useKeyboardShortcuts";

// Settings store
export {
	type DateFormat,
	type LogLevel,
	type SettingsStore,
	type TableDensity,
	type ThemeSetting,
	type TimezoneOption,
	useDateFormatSetting,
	useItemsPerPage,
	useRefreshInterval,
	useSettingsStore,
	useTableDensity,
	useThemeSetting,
	useTimezone,
} from "./useSettings";

// Task hooks
export {
	taskKeys,
	useBulkDeleteTasks,
	useBulkRetryTasks,
	useDeleteTask,
	useInvalidateTasks,
	usePrefetchTask,
	useRetryTask,
	useTask,
	useTasks,
} from "./useTasks";
// Other hooks
export { useTheme } from "./useTheme";
export { useWebSocket } from "./useWebSocket";
// Worker hooks
export {
	useInvalidateWorkers,
	useKillWorker,
	usePauseWorker,
	usePrefetchWorker,
	useResumeWorker,
	useShutdownWorker,
	useWorker,
	useWorkerAction,
	useWorkerDetail,
	useWorkerLogs,
	useWorkers,
	workerKeys,
} from "./useWorkers";

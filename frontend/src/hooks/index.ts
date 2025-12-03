/**
 * Central export for all React Query hooks.
 */

// Dashboard hooks
export {
	dashboardKeys,
	useDashboardSummary,
	useInvalidateDashboard,
	usePrefetchQueue,
	usePrefetchWorker,
	useQueue,
	useQueues,
	useWorker,
	useWorkers,
} from "./useDashboard";

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

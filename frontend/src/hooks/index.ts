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

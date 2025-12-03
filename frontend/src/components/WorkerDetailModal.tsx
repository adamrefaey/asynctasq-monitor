/**
 * WorkerDetailModal component for displaying comprehensive worker information.
 *
 * Built with React Aria Components for accessibility.
 * Uses TanStack Query v5 hooks for data fetching and mutations.
 *
 * Follows Week 5 Worker View specifications from the implementation plan.
 */

import {
	Activity,
	AlertTriangle,
	Calendar,
	Check,
	Clock,
	Copy,
	Cpu,
	HardDrive,
	Hash,
	Layers,
	MemoryStick,
	Pause,
	Play,
	Power,
	RefreshCw,
	Server,
	Tag,
	Timer,
	XCircle,
	Zap,
} from "lucide-react";
import { type ReactNode, useState } from "react";
import { Badge, type BadgeVariant } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DialogTrigger, Modal, ModalDialog } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import {
	useKillWorker,
	usePauseWorker,
	useResumeWorker,
	useShutdownWorker,
	useWorkerDetail,
} from "@/hooks/useWorkers";
import type { Worker, WorkerDetail, WorkerStatus, WorkerTask } from "@/lib/types";

// ============================================================================
// Types
// ============================================================================

interface WorkerDetailModalProps {
	/** Worker ID to display */
	workerId: string;
	/** Whether the modal is open */
	isOpen: boolean;
	/** Callback when modal is closed */
	onClose: () => void;
	/** Callback when worker action is performed */
	onActionPerformed?: () => void;
}

interface WorkerDetailTriggerProps {
	/** Worker to display in modal */
	worker: Worker;
	/** Render prop for trigger button */
	children: ReactNode;
}

// ============================================================================
// Helper Components
// ============================================================================

interface DetailRowProps {
	label: string;
	children: ReactNode;
	icon?: ReactNode;
}

function DetailRow({ label, children, icon }: DetailRowProps): ReactNode {
	return (
		<div className="flex items-start gap-3 py-2">
			{icon && <span className="mt-0.5 text-zinc-400 dark:text-zinc-500">{icon}</span>}
			<div className="flex-1 min-w-0">
				<dt className="text-sm font-medium text-zinc-500 dark:text-zinc-400">{label}</dt>
				<dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">{children}</dd>
			</div>
		</div>
	);
}

interface CopyButtonProps {
	text: string;
	label: string;
}

function CopyButton({ text, label }: CopyButtonProps): ReactNode {
	const [copied, setCopied] = useState(false);

	const handleCopy = async () => {
		await navigator.clipboard.writeText(text);
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	};

	return (
		<Button variant="ghost" size="icon-sm" onPress={handleCopy} aria-label={label}>
			{copied ? (
				<Check className="h-3.5 w-3.5 text-emerald-500" />
			) : (
				<Copy className="h-3.5 w-3.5" />
			)}
		</Button>
	);
}

function formatDateTime(isoString: string | null | undefined): string {
	if (!isoString) return "—";
	const date = new Date(isoString);
	return new Intl.DateTimeFormat("en-US", {
		dateStyle: "medium",
		timeStyle: "medium",
	}).format(date);
}

function formatDuration(ms: number | null | undefined): string {
	if (ms === null || ms === undefined) return "—";
	if (ms < 1000) return `${ms}ms`;
	if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
	const minutes = Math.floor(ms / 60000);
	const seconds = ((ms % 60000) / 1000).toFixed(1);
	return `${minutes}m ${seconds}s`;
}

function formatUptime(seconds: number): string {
	if (seconds < 60) return `${seconds}s`;
	if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
	if (seconds < 86400) {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		return `${hours}h ${minutes}m`;
	}
	const days = Math.floor(seconds / 86400);
	const hours = Math.floor((seconds % 86400) / 3600);
	return `${days}d ${hours}h`;
}

function formatPercentage(value: number | null | undefined): string {
	if (value === null || value === undefined) return "—";
	return `${value.toFixed(1)}%`;
}

function getWorkerStatusBadgeVariant(status: WorkerStatus): BadgeVariant {
	const statusMap: Record<WorkerStatus, BadgeVariant> = {
		active: "success",
		idle: "info",
		offline: "error",
	};
	return statusMap[status] ?? "default";
}

const STATUS_ICONS: Record<WorkerStatus, ReactNode> = {
	active: <Play className="h-4 w-4" />,
	idle: <Clock className="h-4 w-4" />,
	offline: <XCircle className="h-4 w-4" />,
};

function getStatusIcon(status: WorkerStatus): ReactNode {
	return STATUS_ICONS[status] ?? null;
}

function WorkerLoadingState(): ReactNode {
	return (
		<div className="flex items-center justify-center p-12">
			<Spinner size="lg" />
		</div>
	);
}

function WorkerErrorState({ message }: { message: string }): ReactNode {
	return (
		<div className="flex flex-col items-center justify-center p-12 text-center">
			<AlertTriangle className="h-12 w-12 text-red-500 mb-4" />
			<p className="text-sm text-zinc-600 dark:text-zinc-400">Failed to load worker details</p>
			<p className="text-xs text-zinc-500 mt-1">{message}</p>
		</div>
	);
}

// ============================================================================
// Section Components
// ============================================================================

interface WorkerOverviewSectionProps {
	worker: WorkerDetail;
}

function WorkerOverviewSection({ worker }: WorkerOverviewSectionProps): ReactNode {
	return (
		<div className="p-4">
			<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">Overview</h4>
			<dl className="grid grid-cols-2 gap-x-4">
				<DetailRow label="Hostname" icon={<Server className="h-4 w-4" />}>
					{worker.hostname ?? "Unknown"}
				</DetailRow>
				<DetailRow label="Process ID" icon={<Hash className="h-4 w-4" />}>
					{worker.pid ?? "—"}
				</DetailRow>
				<DetailRow label="Started" icon={<Calendar className="h-4 w-4" />}>
					{formatDateTime(worker.started_at)}
				</DetailRow>
				<DetailRow label="Uptime" icon={<Timer className="h-4 w-4" />}>
					{formatUptime(worker.uptime_seconds)}
				</DetailRow>
				<DetailRow label="Last Heartbeat" icon={<Activity className="h-4 w-4" />}>
					{formatDateTime(worker.last_heartbeat)}
				</DetailRow>
				<DetailRow label="Version" icon={<Tag className="h-4 w-4" />}>
					{worker.version ?? "—"}
				</DetailRow>
			</dl>
		</div>
	);
}

interface WorkerResourcesSectionProps {
	worker: WorkerDetail;
}

function WorkerResourcesSection({ worker }: WorkerResourcesSectionProps): ReactNode {
	return (
		<div className="p-4">
			<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">Resources</h4>
			<div className="grid grid-cols-3 gap-4">
				{/* CPU Usage */}
				<div className="text-center p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
					<Cpu className="h-5 w-5 mx-auto text-zinc-400 mb-2" />
					<div className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
						{formatPercentage(worker.cpu_usage)}
					</div>
					<div className="text-xs text-zinc-500">CPU Usage</div>
				</div>
				{/* Memory Usage */}
				<div className="text-center p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
					<MemoryStick className="h-5 w-5 mx-auto text-zinc-400 mb-2" />
					<div className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
						{formatPercentage(worker.memory_usage)}
					</div>
					<div className="text-xs text-zinc-500">Memory Usage</div>
				</div>
				{/* Memory MB */}
				<div className="text-center p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
					<HardDrive className="h-5 w-5 mx-auto text-zinc-400 mb-2" />
					<div className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
						{worker.memory_mb ? `${worker.memory_mb}MB` : "—"}
					</div>
					<div className="text-xs text-zinc-500">Memory Used</div>
				</div>
			</div>
		</div>
	);
}

interface WorkerPerformanceSectionProps {
	worker: WorkerDetail;
}

function WorkerPerformanceSection({ worker }: WorkerPerformanceSectionProps): ReactNode {
	return (
		<div className="p-4">
			<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">Performance</h4>
			<div className="grid grid-cols-4 gap-4">
				{/* Tasks Processed */}
				<div className="text-center p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
					<div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
						{worker.tasks_processed.toLocaleString()}
					</div>
					<div className="text-xs text-zinc-500">Processed</div>
				</div>
				{/* Tasks Failed */}
				<div className="text-center p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
					<div className="text-xl font-bold text-red-600 dark:text-red-400">
						{worker.tasks_failed.toLocaleString()}
					</div>
					<div className="text-xs text-zinc-500">Failed</div>
				</div>
				{/* Success Rate */}
				<div className="text-center p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
					<div className="text-xl font-bold text-blue-600 dark:text-blue-400">
						{worker.success_rate.toFixed(1)}%
					</div>
					<div className="text-xs text-zinc-500">Success Rate</div>
				</div>
				{/* Tasks/Hour */}
				<div className="text-center p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
					<div className="text-xl font-bold text-amber-600 dark:text-amber-400">
						{worker.tasks_per_hour.toFixed(1)}
					</div>
					<div className="text-xs text-zinc-500">Tasks/Hour</div>
				</div>
			</div>
		</div>
	);
}

interface WorkerCurrentTaskSectionProps {
	worker: WorkerDetail;
}

function WorkerCurrentTaskSection({ worker }: WorkerCurrentTaskSectionProps): ReactNode {
	if (!worker.current_task_id) return null;

	return (
		<div className="p-4 bg-cyan-50 dark:bg-cyan-900/20 border-l-4 border-cyan-500">
			<h4 className="text-sm font-medium text-cyan-800 dark:text-cyan-300 mb-2 flex items-center gap-2">
				<Zap className="h-4 w-4" />
				Currently Processing
			</h4>
			<div className="flex items-center gap-3">
				<code className="text-sm text-cyan-700 dark:text-cyan-400 font-mono">
					{worker.current_task_name}
				</code>
				<span className="text-xs text-cyan-600 dark:text-cyan-500">
					ID: {worker.current_task_id}
				</span>
				{worker.current_task_started_at && (
					<span className="text-xs text-cyan-600 dark:text-cyan-500">
						Started {formatDateTime(worker.current_task_started_at)}
					</span>
				)}
			</div>
		</div>
	);
}

interface WorkerQueuesSectionProps {
	worker: WorkerDetail;
}

function WorkerQueuesSection({ worker }: WorkerQueuesSectionProps): ReactNode {
	return (
		<div className="p-4">
			<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3 flex items-center gap-2">
				<Layers className="h-4 w-4" />
				Subscribed Queues
			</h4>
			<div className="flex flex-wrap gap-2">
				{worker.queues.map((queue) => (
					<Badge key={queue} variant="info" size="md">
						{queue}
					</Badge>
				))}
			</div>
		</div>
	);
}

interface WorkerRecentTasksSectionProps {
	worker: WorkerDetail;
}

function WorkerRecentTasksSection({ worker }: WorkerRecentTasksSectionProps): ReactNode {
	if (!worker.recent_tasks || worker.recent_tasks.length === 0) return null;

	const getTaskStatusVariant = (status: string): BadgeVariant => {
		const statusMap: Record<string, BadgeVariant> = {
			completed: "success",
			failed: "error",
			running: "running",
			pending: "pending",
		};
		return statusMap[status] ?? "default";
	};

	return (
		<div className="p-4">
			<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">Recent Tasks</h4>
			<div className="space-y-2 max-h-48 overflow-y-auto">
				{worker.recent_tasks.slice(0, 10).map((task: WorkerTask) => (
					<div
						key={task.id}
						className="flex items-center justify-between p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800"
					>
						<div className="flex items-center gap-3 min-w-0">
							<Badge variant={getTaskStatusVariant(task.status)} size="sm">
								{task.status}
							</Badge>
							<span className="text-sm font-mono text-zinc-700 dark:text-zinc-300 truncate">
								{task.name}
							</span>
						</div>
						<div className="flex items-center gap-3 text-xs text-zinc-500">
							<span>{task.queue}</span>
							{task.duration_ms && <span>{formatDuration(task.duration_ms)}</span>}
						</div>
					</div>
				))}
			</div>
		</div>
	);
}

interface WorkerTagsSectionProps {
	worker: WorkerDetail;
}

function WorkerTagsSection({ worker }: WorkerTagsSectionProps): ReactNode {
	if (!worker.tags || worker.tags.length === 0) return null;

	return (
		<div className="p-4">
			<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">Tags</h4>
			<div className="flex flex-wrap gap-2">
				{worker.tags.map((tag) => (
					<Badge key={tag} variant="default" size="sm">
						{tag}
					</Badge>
				))}
			</div>
		</div>
	);
}

// ============================================================================
// Main Content Body
// ============================================================================

interface WorkerContentBodyProps {
	worker: WorkerDetail;
}

function WorkerContentBody({ worker }: WorkerContentBodyProps): ReactNode {
	return (
		<Modal.Body className="space-y-6 p-0">
			{/* Header with status */}
			<div className="flex items-start justify-between gap-4 px-6 pt-6">
				<div className="min-w-0 flex-1">
					<h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 truncate">
						{worker.name}
					</h3>
					<div className="flex items-center gap-2 mt-1">
						<code className="text-xs text-zinc-500 dark:text-zinc-400 truncate max-w-[200px]">
							{worker.id}
						</code>
						<CopyButton text={worker.id} label="Copy worker ID" />
					</div>
				</div>
				<div className="flex items-center gap-2">
					{worker.is_paused && (
						<Badge variant="warning" size="md">
							<Pause className="h-3 w-3 mr-1" />
							Paused
						</Badge>
					)}
					<Badge variant={getWorkerStatusBadgeVariant(worker.status)} size="lg" dot>
						{getStatusIcon(worker.status)}
						<span className="ml-1 capitalize">{worker.status}</span>
					</Badge>
				</div>
			</div>

			{/* Current Task Alert */}
			<WorkerCurrentTaskSection worker={worker} />

			{/* Main sections in bordered container */}
			<div className="mx-6 rounded-lg border border-zinc-200 dark:border-zinc-700 divide-y divide-zinc-200 dark:divide-zinc-700">
				<WorkerOverviewSection worker={worker} />
				<WorkerResourcesSection worker={worker} />
				<WorkerPerformanceSection worker={worker} />
			</div>

			{/* Queues */}
			<div className="px-6">
				<WorkerQueuesSection worker={worker} />
			</div>

			{/* Recent Tasks */}
			<div className="px-6 pb-6">
				<WorkerRecentTasksSection worker={worker} />
			</div>

			{/* Tags */}
			<div className="px-6 pb-6">
				<WorkerTagsSection worker={worker} />
			</div>
		</Modal.Body>
	);
}

// ============================================================================
// Modal Footer with Actions
// ============================================================================

interface WorkerModalFooterProps {
	worker: WorkerDetail;
	onClose: () => void;
	onActionPerformed?: () => void;
}

function WorkerModalFooter({
	worker,
	onClose,
	onActionPerformed,
}: WorkerModalFooterProps): ReactNode {
	const { mutate: pauseWorker, isPending: isPausing } = usePauseWorker();
	const { mutate: resumeWorker, isPending: isResuming } = useResumeWorker();
	const { mutate: shutdownWorker, isPending: isShuttingDown } = useShutdownWorker();
	const { mutate: killWorker, isPending: isKilling } = useKillWorker();

	const isOffline = worker.status === "offline";
	const anyPending = isPausing || isResuming || isShuttingDown || isKilling;

	const handlePause = () => {
		pauseWorker({ workerId: worker.id }, { onSuccess: () => onActionPerformed?.() });
	};

	const handleResume = () => {
		resumeWorker({ workerId: worker.id }, { onSuccess: () => onActionPerformed?.() });
	};

	const handleShutdown = () => {
		shutdownWorker({ workerId: worker.id }, { onSuccess: () => onActionPerformed?.() });
	};

	const handleKill = () => {
		killWorker({ workerId: worker.id, force: false }, { onSuccess: () => onActionPerformed?.() });
	};

	return (
		<Modal.Footer>
			<Button variant="outline" onPress={onClose}>
				Close
			</Button>

			{/* Pause/Resume button */}
			{!isOffline &&
				(worker.is_paused ? (
					<Button variant="secondary" onPress={handleResume} isDisabled={anyPending}>
						{isResuming ? (
							<>
								<Spinner size="sm" className="mr-2" />
								Resuming...
							</>
						) : (
							<>
								<Play className="h-4 w-4 mr-2" />
								Resume
							</>
						)}
					</Button>
				) : (
					<Button variant="secondary" onPress={handlePause} isDisabled={anyPending}>
						{isPausing ? (
							<>
								<Spinner size="sm" className="mr-2" />
								Pausing...
							</>
						) : (
							<>
								<Pause className="h-4 w-4 mr-2" />
								Pause
							</>
						)}
					</Button>
				))}

			{/* Shutdown button */}
			{!isOffline && (
				<Button variant="outline" onPress={handleShutdown} isDisabled={anyPending}>
					{isShuttingDown ? (
						<>
							<Spinner size="sm" className="mr-2" />
							Shutting Down...
						</>
					) : (
						<>
							<Power className="h-4 w-4 mr-2" />
							Shutdown
						</>
					)}
				</Button>
			)}

			{/* Kill button */}
			{!isOffline && (
				<Button variant="danger" onPress={handleKill} isDisabled={anyPending}>
					{isKilling ? (
						<>
							<Spinner size="sm" className="mr-2" />
							Killing...
						</>
					) : (
						<>
							<XCircle className="h-4 w-4 mr-2" />
							Kill
						</>
					)}
				</Button>
			)}
		</Modal.Footer>
	);
}

// ============================================================================
// Main Modal Component
// ============================================================================

/**
 * Modal component for displaying detailed worker information with management actions.
 *
 * @example
 * ```tsx
 * const [selectedWorkerId, setSelectedWorkerId] = useState<string | null>(null);
 *
 * <WorkerDetailModal
 *   workerId={selectedWorkerId!}
 *   isOpen={selectedWorkerId !== null}
 *   onClose={() => setSelectedWorkerId(null)}
 * />
 * ```
 */
export function WorkerDetailModal({
	workerId,
	isOpen,
	onClose,
	onActionPerformed,
}: WorkerDetailModalProps): ReactNode {
	const { data: worker, isPending, error } = useWorkerDetail({ workerId });

	return (
		<Modal isOpen={isOpen} onOpenChange={(open) => !open && onClose()} size="2xl">
			<ModalDialog title="Worker Details">
				<Modal.Content>
					{isPending && <WorkerLoadingState />}
					{error && <WorkerErrorState message={error.message} />}
					{worker && <WorkerContentBody worker={worker} />}
				</Modal.Content>

				{worker && (
					<WorkerModalFooter
						worker={worker}
						onClose={onClose}
						{...(onActionPerformed && { onActionPerformed })}
					/>
				)}
			</ModalDialog>
		</Modal>
	);
}

/**
 * Trigger component that wraps children and opens WorkerDetail modal on click.
 *
 * @example
 * ```tsx
 * <WorkerDetailTrigger worker={worker}>
 *   <Button variant="ghost">View Details</Button>
 * </WorkerDetailTrigger>
 * ```
 */
export function WorkerDetailTrigger({ worker, children }: WorkerDetailTriggerProps): ReactNode {
	return (
		<DialogTrigger>
			{children}
			<Modal size="2xl">
				<ModalDialog title="Worker Details">
					<Modal.Body className="space-y-6 p-6">
						{/* Header with status */}
						<div className="flex items-start justify-between gap-4">
							<div className="min-w-0 flex-1">
								<h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 truncate">
									{worker.name}
								</h3>
								<div className="flex items-center gap-2 mt-1">
									<code className="text-xs text-zinc-500 dark:text-zinc-400 truncate max-w-[200px]">
										{worker.id}
									</code>
									<CopyButton text={worker.id} label="Copy worker ID" />
								</div>
							</div>
							<Badge variant={getWorkerStatusBadgeVariant(worker.status)} size="lg" dot>
								{getStatusIcon(worker.status)}
								<span className="ml-1 capitalize">{worker.status}</span>
							</Badge>
						</div>

						{/* Quick stats grid */}
						<div className="grid grid-cols-3 gap-4">
							<div className="text-center p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
								<div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
									{worker.tasks_processed.toLocaleString()}
								</div>
								<div className="text-xs text-zinc-500">Processed</div>
							</div>
							<div className="text-center p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
								<div className="text-xl font-bold text-red-600 dark:text-red-400">
									{worker.tasks_failed.toLocaleString()}
								</div>
								<div className="text-xs text-zinc-500">Failed</div>
							</div>
							<div className="text-center p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800">
								<div className="text-xl font-bold text-blue-600 dark:text-blue-400">
									{formatUptime(worker.uptime_seconds)}
								</div>
								<div className="text-xs text-zinc-500">Uptime</div>
							</div>
						</div>

						{/* Queues */}
						<div>
							<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">Queues</h4>
							<div className="flex flex-wrap gap-2">
								{worker.queues.map((queue) => (
									<Badge key={queue} variant="info">
										{queue}
									</Badge>
								))}
							</div>
						</div>

						{/* Current task if processing */}
						{worker.current_task_id && (
							<div className="p-3 rounded-lg bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800">
								<div className="flex items-center gap-2 text-cyan-700 dark:text-cyan-400">
									<RefreshCw className="h-4 w-4 animate-spin" />
									<span className="text-sm">
										Processing: <code>{worker.current_task_name}</code>
									</span>
								</div>
							</div>
						)}
					</Modal.Body>
				</ModalDialog>
			</Modal>
		</DialogTrigger>
	);
}

export default WorkerDetailModal;

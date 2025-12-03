/**
 * TaskDetail modal component for displaying complete task information.
 *
 * Built with React Aria Components for accessibility.
 * Uses TanStack Query v5 hooks for data fetching.
 */

import {
	AlertTriangle,
	Calendar,
	Check,
	Clock,
	Copy,
	Play,
	RefreshCw,
	Timer,
	Trash2,
	User,
	X,
} from "lucide-react";
import { type ReactNode, useState } from "react";
import { Badge, getTaskStatusBadgeVariant } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DialogTrigger, Modal, ModalDialog } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { useDeleteTask, useRetryTask, useTask } from "@/hooks/useTasks";
import type { Task, TaskStatus } from "@/lib/types";

// ============================================================================
// Types
// ============================================================================

interface TaskDetailModalProps {
	/** Task ID to display */
	taskId: string;
	/** Whether the modal is open */
	isOpen: boolean;
	/** Callback when modal is closed */
	onClose: () => void;
	/** Callback when task is deleted */
	onDeleted?: () => void;
	/** Callback when task is retried */
	onRetried?: () => void;
}

interface TaskDetailTriggerProps {
	/** Task to display in modal */
	task: Task;
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

interface CodeBlockProps {
	code: string;
	label: string;
}

function CodeBlock({ code, label }: CodeBlockProps): ReactNode {
	return (
		<div className="relative mt-1 group">
			<pre className="rounded-lg bg-zinc-100 dark:bg-zinc-800 p-3 text-xs font-mono overflow-x-auto max-h-48 overflow-y-auto">
				{code}
			</pre>
			<div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
				<CopyButton text={code} label={`Copy ${label}`} />
			</div>
		</div>
	);
}

function formatDateTime(isoString: string | null): string {
	if (!isoString) return "—";
	const date = new Date(isoString);
	return new Intl.DateTimeFormat("en-US", {
		dateStyle: "medium",
		timeStyle: "medium",
	}).format(date);
}

function formatDuration(ms: number | null): string {
	if (ms === null) return "—";
	if (ms < 1000) return `${ms}ms`;
	if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
	const minutes = Math.floor(ms / 60000);
	const seconds = ((ms % 60000) / 1000).toFixed(1);
	return `${minutes}m ${seconds}s`;
}

const STATUS_ICONS: Record<TaskStatus, ReactNode> = {
	pending: <Clock className="h-4 w-4" />,
	running: <Play className="h-4 w-4" />,
	completed: <Check className="h-4 w-4" />,
	failed: <X className="h-4 w-4" />,
	retrying: <RefreshCw className="h-4 w-4" />,
	cancelled: <X className="h-4 w-4" />,
};

function getStatusIcon(status: TaskStatus): ReactNode {
	return STATUS_ICONS[status] ?? null;
}

function TaskLoadingState(): ReactNode {
	return (
		<div className="flex items-center justify-center p-12">
			<Spinner size="lg" />
		</div>
	);
}

function TaskErrorState({ message }: { message: string }): ReactNode {
	return (
		<div className="flex flex-col items-center justify-center p-12 text-center">
			<AlertTriangle className="h-12 w-12 text-red-500 mb-4" />
			<p className="text-sm text-zinc-600 dark:text-zinc-400">Failed to load task details</p>
			<p className="text-xs text-zinc-500 mt-1">{message}</p>
		</div>
	);
}

function TaskTimingSection({ task }: { task: Task }): ReactNode {
	return (
		<div className="p-4">
			<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">Timing</h4>
			<dl className="grid grid-cols-2 gap-x-4">
				<DetailRow label="Enqueued" icon={<Calendar className="h-4 w-4" />}>
					{formatDateTime(task.enqueued_at)}
				</DetailRow>
				<DetailRow label="Started" icon={<Play className="h-4 w-4" />}>
					{formatDateTime(task.started_at)}
				</DetailRow>
				<DetailRow label="Completed" icon={<Check className="h-4 w-4" />}>
					{formatDateTime(task.completed_at)}
				</DetailRow>
				<DetailRow label="Duration" icon={<Timer className="h-4 w-4" />}>
					{formatDuration(task.duration_ms)}
				</DetailRow>
			</dl>
		</div>
	);
}

function TaskExecutionSection({ task }: { task: Task }): ReactNode {
	return (
		<div className="p-4">
			<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">Execution</h4>
			<dl className="grid grid-cols-2 gap-x-4">
				<DetailRow label="Queue">
					<Badge variant="info">{task.queue}</Badge>
				</DetailRow>
				<DetailRow label="Worker" icon={<User className="h-4 w-4" />}>
					{task.worker_id ?? "Not assigned"}
				</DetailRow>
				<DetailRow label="Attempt">
					{task.attempt} / {task.max_retries}
				</DetailRow>
				<DetailRow label="Priority">{task.priority}</DetailRow>
			</dl>
		</div>
	);
}

function TaskArgumentsSection({ task }: { task: Task }): ReactNode {
	const hasArgs = task.args.length > 0;
	const hasKwargs = Object.keys(task.kwargs).length > 0;

	if (!hasArgs && !hasKwargs) return null;

	return (
		<div>
			<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">Arguments</h4>
			{hasArgs && (
				<div className="mb-3">
					<p className="text-xs text-zinc-500 mb-1">Positional</p>
					<CodeBlock code={JSON.stringify(task.args, null, 2)} label="positional arguments" />
				</div>
			)}
			{hasKwargs && (
				<div>
					<p className="text-xs text-zinc-500 mb-1">Keyword</p>
					<CodeBlock code={JSON.stringify(task.kwargs, null, 2)} label="keyword arguments" />
				</div>
			)}
		</div>
	);
}

function TaskErrorSection({ task }: { task: Task }): ReactNode {
	if (!task.exception) return null;

	return (
		<div className="rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-900/20 p-4">
			<div className="flex items-start gap-3">
				<AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
				<div className="flex-1 min-w-0">
					<h4 className="text-sm font-medium text-red-800 dark:text-red-300">Error</h4>
					<p className="mt-1 text-sm text-red-700 dark:text-red-400">{task.exception}</p>
					{task.traceback && (
						<details className="mt-3">
							<summary className="text-xs text-red-600 dark:text-red-400 cursor-pointer hover:underline">
								View traceback
							</summary>
							<pre className="mt-2 text-xs text-red-700 dark:text-red-400 overflow-x-auto whitespace-pre-wrap">
								{task.traceback}
							</pre>
						</details>
					)}
				</div>
			</div>
		</div>
	);
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Modal component for displaying detailed task information.
 *
 * @example
 * ```tsx
 * const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
 *
 * <TaskDetailModal
 *   taskId={selectedTaskId!}
 *   isOpen={selectedTaskId !== null}
 *   onClose={() => setSelectedTaskId(null)}
 * />
 * ```
 */
function TaskContentBody({ task }: { task: Task }): ReactNode {
	return (
		<Modal.Body className="space-y-6">
			{/* Header with status */}
			<div className="flex items-start justify-between gap-4">
				<div className="min-w-0 flex-1">
					<h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 truncate">
						{task.name}
					</h3>
					<div className="flex items-center gap-2 mt-1">
						<code className="text-xs text-zinc-500 dark:text-zinc-400 truncate max-w-[200px]">
							{task.id}
						</code>
						<CopyButton text={task.id} label="Copy task ID" />
					</div>
				</div>
				<Badge variant={getTaskStatusBadgeVariant(task.status)} size="lg" dot>
					{getStatusIcon(task.status)}
					<span className="ml-1 capitalize">{task.status}</span>
				</Badge>
			</div>

			{/* Timing and Execution Information */}
			<div className="rounded-lg border border-zinc-200 dark:border-zinc-700 divide-y divide-zinc-200 dark:divide-zinc-700">
				<TaskTimingSection task={task} />
				<TaskExecutionSection task={task} />
			</div>

			{/* Task Arguments */}
			<TaskArgumentsSection task={task} />

			{/* Result */}
			{task.result !== null && task.result !== undefined && (
				<div>
					<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">Result</h4>
					<CodeBlock code={JSON.stringify(task.result, null, 2)} label="result" />
				</div>
			)}

			{/* Error Information */}
			<TaskErrorSection task={task} />

			{/* Tags */}
			{task.tags.length > 0 && (
				<div>
					<h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">Tags</h4>
					<div className="flex flex-wrap gap-2">
						{task.tags.map((tag) => (
							<Badge key={tag} variant="default" size="sm">
								{tag}
							</Badge>
						))}
					</div>
				</div>
			)}
		</Modal.Body>
	);
}

interface TaskModalFooterProps {
	task: Task;
	onClose: () => void;
	onRetry: () => void;
	onDelete: () => void;
	isRetrying: boolean;
	isDeleting: boolean;
}

function TaskModalFooter({
	task,
	onClose,
	onRetry,
	onDelete,
	isRetrying,
	isDeleting,
}: TaskModalFooterProps): ReactNode {
	const canRetry = task.status === "failed" && (task.attempt ?? 0) < (task.max_retries ?? 0);

	return (
		<Modal.Footer>
			<Button variant="outline" onPress={onClose}>
				Close
			</Button>
			{canRetry && (
				<Button variant="secondary" onPress={onRetry} isDisabled={isRetrying}>
					{isRetrying ? (
						<>
							<Spinner size="sm" className="mr-2" />
							Retrying...
						</>
					) : (
						<>
							<RefreshCw className="h-4 w-4 mr-2" />
							Retry Task
						</>
					)}
				</Button>
			)}
			<Button variant="danger" onPress={onDelete} isDisabled={isDeleting}>
				{isDeleting ? (
					<>
						<Spinner size="sm" className="mr-2" />
						Deleting...
					</>
				) : (
					<>
						<Trash2 className="h-4 w-4 mr-2" />
						Delete
					</>
				)}
			</Button>
		</Modal.Footer>
	);
}

export function TaskDetailModal({
	taskId,
	isOpen,
	onClose,
	onDeleted,
	onRetried,
}: TaskDetailModalProps): ReactNode {
	const { data: task, isPending, error } = useTask({ taskId });
	const { mutate: retryTask, isPending: isRetrying } = useRetryTask();
	const { mutate: deleteTask, isPending: isDeleting } = useDeleteTask();

	const handleRetry = () => {
		retryTask({ taskId }, { onSuccess: () => onRetried?.() });
	};

	const handleDelete = () => {
		deleteTask(
			{ taskId },
			{
				onSuccess: () => {
					onClose();
					onDeleted?.();
				},
			},
		);
	};

	return (
		<Modal isOpen={isOpen} onOpenChange={(open) => !open && onClose()} size="xl">
			<ModalDialog title="Task Details">
				<Modal.Content>
					{isPending && <TaskLoadingState />}
					{error && <TaskErrorState message={error.message} />}
					{task && <TaskContentBody task={task} />}
				</Modal.Content>

				{task && (
					<TaskModalFooter
						task={task}
						onClose={onClose}
						onRetry={handleRetry}
						onDelete={handleDelete}
						isRetrying={isRetrying}
						isDeleting={isDeleting}
					/>
				)}
			</ModalDialog>
		</Modal>
	);
}

/**
 * Trigger component that wraps children and opens TaskDetail modal on click.
 *
 * @example
 * ```tsx
 * <TaskDetailTrigger task={task}>
 *   <Button variant="ghost">View Details</Button>
 * </TaskDetailTrigger>
 * ```
 */
export function TaskDetailTrigger({ task, children }: TaskDetailTriggerProps): ReactNode {
	return (
		<DialogTrigger>
			{children}
			<Modal size="xl">
				<ModalDialog title="Task Details">
					<Modal.Body className="space-y-6">
						{/* Inline task details using the same layout */}
						<div className="flex items-start justify-between gap-4">
							<div className="min-w-0 flex-1">
								<h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 truncate">
									{task.name}
								</h3>
								<div className="flex items-center gap-2 mt-1">
									<code className="text-xs text-zinc-500 dark:text-zinc-400 truncate max-w-[200px]">
										{task.id}
									</code>
									<CopyButton text={task.id} label="Copy task ID" />
								</div>
							</div>
							<Badge variant={getTaskStatusBadgeVariant(task.status)} size="lg" dot>
								{getStatusIcon(task.status)}
								<span className="ml-1 capitalize">{task.status}</span>
							</Badge>
						</div>

						{/* Show inline task data (simplified version) */}
						<div className="rounded-lg border border-zinc-200 dark:border-zinc-700 p-4">
							<dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
								<div>
									<dt className="text-zinc-500">Queue</dt>
									<dd>{task.queue}</dd>
								</div>
								<div>
									<dt className="text-zinc-500">Duration</dt>
									<dd>{formatDuration(task.duration_ms)}</dd>
								</div>
								<div>
									<dt className="text-zinc-500">Attempt</dt>
									<dd>
										{task.attempt} / {task.max_retries}
									</dd>
								</div>
								<div>
									<dt className="text-zinc-500">Enqueued</dt>
									<dd>{formatDateTime(task.enqueued_at)}</dd>
								</div>
							</dl>
						</div>

						{/* Error display if failed */}
						{task.exception && (
							<div className="rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-900/20 p-4">
								<div className="flex items-start gap-2">
									<AlertTriangle className="h-4 w-4 text-red-500 mt-0.5" />
									<p className="text-sm text-red-700 dark:text-red-400">{task.exception}</p>
								</div>
							</div>
						)}
					</Modal.Body>
				</ModalDialog>
			</Modal>
		</DialogTrigger>
	);
}

export default TaskDetailModal;

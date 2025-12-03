/**
 * Workers monitoring and management page.
 *
 * Week 5 implementation following the monitoring-ui wireframes.
 * Features:
 * - Real-time worker status updates via polling
 * - Worker filtering by status, queue, search
 * - Worker detail modal with comprehensive info
 * - Management actions (pause, resume, shutdown, kill)
 * - Resource usage visualization
 */

import { formatDistanceToNow } from "date-fns";
import {
	Activity,
	CheckCircle2,
	Clock,
	Cpu,
	HardDrive,
	MemoryStick,
	Pause,
	Play,
	Power,
	RefreshCw,
	Server,
	XCircle,
	Zap,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Badge, Button, Card, Spinner, TextField } from "@/components/ui";
import { WorkerDetailModal } from "@/components/WorkerDetailModal";
import {
	useInvalidateWorkers,
	usePauseWorker,
	usePrefetchWorker,
	useResumeWorker,
	useWorkers,
} from "@/hooks/useWorkers";
import type { Worker, WorkerFilters, WorkerStatus } from "@/lib/types";

const statusConfig: Record<
	WorkerStatus,
	{ color: "success" | "warning" | "error" | "default"; icon: typeof Activity }
> = {
	active: { color: "success", icon: Activity },
	idle: { color: "warning", icon: Clock },
	offline: { color: "error", icon: XCircle },
};

function WorkerStatusBadge({ status }: { status: WorkerStatus }) {
	const config = statusConfig[status];
	const Icon = config.icon;

	return (
		<Badge variant={config.color} className="inline-flex items-center gap-1">
			<Icon className="h-3 w-3" />
			{status}
		</Badge>
	);
}

function ResourceMeter({
	label,
	value,
	max,
	icon: Icon,
	unit = "%",
}: {
	label: string;
	value: number;
	max: number;
	icon: typeof Cpu;
	unit?: string;
}) {
	const percentage = Math.round((value / max) * 100);
	const colorClass =
		percentage > 80 ? "bg-red-500" : percentage > 60 ? "bg-yellow-500" : "bg-green-500";

	return (
		<div className="space-y-1">
			<div className="flex items-center justify-between text-sm">
				<span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
					<Icon className="h-3.5 w-3.5" />
					{label}
				</span>
				<span className="font-medium text-gray-900 dark:text-white">
					{unit === "%" ? `${percentage}%` : `${value}/${max}${unit}`}
				</span>
			</div>
			<div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
				<div
					className={`h-full rounded-full transition-all duration-300 ${colorClass}`}
					style={{ width: `${percentage}%` }}
				/>
			</div>
		</div>
	);
}

function WorkerCard({
	worker,
	onViewDetails,
}: {
	worker: Worker;
	onViewDetails: (workerId: string) => void;
}) {
	const isOnline = worker.status !== "offline";
	const prefetchWorker = usePrefetchWorker();
	const { mutate: pauseWorker, isPending: isPausing } = usePauseWorker();
	const { mutate: resumeWorker, isPending: isResuming } = useResumeWorker();

	const handlePauseResume = () => {
		if (worker.is_paused) {
			resumeWorker({ workerId: worker.id });
		} else {
			pauseWorker({ workerId: worker.id });
		}
	};

	const handleCardClick = () => {
		onViewDetails(worker.id);
	};

	return (
		<Card
			className="hover:border-gray-300 dark:hover:border-gray-600 transition-colors cursor-pointer"
			onClick={handleCardClick}
			onMouseEnter={() => prefetchWorker(worker.id)}
		>
			<Card.Header>
				<div className="flex items-start justify-between">
					<div className="flex items-center gap-3">
						<div
							className={`
              flex h-10 w-10 items-center justify-center rounded-lg
              ${
								isOnline
									? "bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400"
									: "bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500"
							}
            `}
						>
							<Server className="h-5 w-5" />
						</div>
						<div>
							<h3 className="font-semibold text-gray-900 dark:text-white">{worker.name}</h3>
							<p className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-[150px]">
								{worker.id}
							</p>
						</div>
					</div>
					<div className="flex items-center gap-2">
						{worker.is_paused && (
							<Badge variant="warning" size="sm">
								<Pause className="h-3 w-3" />
							</Badge>
						)}
						<WorkerStatusBadge status={worker.status} />
					</div>
				</div>
			</Card.Header>

			<Card.Content className="space-y-4">
				{/* Queues */}
				<div>
					<p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Assigned Queues
					</p>
					<div className="flex flex-wrap gap-1.5">
						{worker.queues.map((queue) => (
							<Badge key={queue} variant="default" size="sm">
								{queue}
							</Badge>
						))}
					</div>
				</div>

				{/* Resource Usage */}
				{isOnline && (
					<div className="space-y-3">
						<p className="text-sm font-medium text-gray-700 dark:text-gray-300">Resource Usage</p>
						<ResourceMeter label="CPU" value={worker.cpu_usage ?? 0} max={100} icon={Cpu} />
						<ResourceMeter
							label="Memory"
							value={worker.memory_usage ?? 0}
							max={100}
							icon={MemoryStick}
						/>
					</div>
				)}

				{/* Current Task */}
				{worker.current_task_id && (
					<div className="rounded-lg bg-cyan-50 dark:bg-cyan-900/20 p-3 border border-cyan-200 dark:border-cyan-800">
						<div className="flex items-center gap-2 text-cyan-700 dark:text-cyan-400">
							<Zap className="h-4 w-4" />
							<span className="text-sm truncate">
								<code className="font-mono">{worker.current_task_name}</code>
							</span>
						</div>
					</div>
				)}

				{/* Stats Grid */}
				<div className="grid grid-cols-2 gap-3">
					<div className="rounded-lg bg-gray-50 dark:bg-gray-800/50 p-3">
						<p className="text-xs text-gray-500 dark:text-gray-400">Tasks Processed</p>
						<p className="font-semibold text-gray-900 dark:text-white">
							{worker.tasks_processed.toLocaleString()}
						</p>
					</div>
					<div className="rounded-lg bg-gray-50 dark:bg-gray-800/50 p-3">
						<p className="text-xs text-gray-500 dark:text-gray-400">Success Rate</p>
						<p className="font-semibold text-gray-900 dark:text-white">
							{worker.success_rate.toFixed(1)}%
						</p>
					</div>
				</div>

				{/* Footer with heartbeat and quick actions */}
				<div className="flex items-center justify-between border-t border-gray-100 dark:border-gray-700 pt-3">
					<span
						className={`text-sm ${
							isOnline ? "text-green-600 dark:text-green-400" : "text-gray-400"
						}`}
					>
						{formatDistanceToNow(new Date(worker.last_heartbeat), {
							addSuffix: true,
						})}
					</span>
					{isOnline && (
						<Button
							variant="ghost"
							size="sm"
							onPress={handlePauseResume}
							isDisabled={isPausing || isResuming}
						>
							{isPausing || isResuming ? (
								<Spinner size="sm" />
							) : worker.is_paused ? (
								<>
									<Play className="h-3 w-3 mr-1" />
									Resume
								</>
							) : (
								<>
									<Pause className="h-3 w-3 mr-1" />
									Pause
								</>
							)}
						</Button>
					)}
				</div>
			</Card.Content>
		</Card>
	);
}

function WorkerStats({ workers }: { workers: Worker[] }) {
	const stats = useMemo(() => {
		const active = workers.filter((w) => w.status === "active").length;
		const idle = workers.filter((w) => w.status === "idle").length;
		const offline = workers.filter((w) => w.status === "offline").length;
		const totalTasks = workers.reduce((sum, w) => sum + w.tasks_processed, 0);

		return { active, idle, offline, total: workers.length, totalTasks };
	}, [workers]);

	return (
		<div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
			<Card>
				<Card.Content className="p-4">
					<div className="flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
							<Server className="h-5 w-5" />
						</div>
						<div>
							<p className="text-sm text-gray-500 dark:text-gray-400">Total Workers</p>
							<p className="text-xl font-bold text-gray-900 dark:text-white">{stats.total}</p>
						</div>
					</div>
				</Card.Content>
			</Card>

			<Card>
				<Card.Content className="p-4">
					<div className="flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400">
							<Activity className="h-5 w-5" />
						</div>
						<div>
							<p className="text-sm text-gray-500 dark:text-gray-400">Active</p>
							<p className="text-xl font-bold text-green-600 dark:text-green-400">{stats.active}</p>
						</div>
					</div>
				</Card.Content>
			</Card>

			<Card>
				<Card.Content className="p-4">
					<div className="flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400">
							<Clock className="h-5 w-5" />
						</div>
						<div>
							<p className="text-sm text-gray-500 dark:text-gray-400">Idle</p>
							<p className="text-xl font-bold text-yellow-600 dark:text-yellow-400">{stats.idle}</p>
						</div>
					</div>
				</Card.Content>
			</Card>

			<Card>
				<Card.Content className="p-4">
					<div className="flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400">
							<Power className="h-5 w-5" />
						</div>
						<div>
							<p className="text-sm text-gray-500 dark:text-gray-400">Offline</p>
							<p className="text-xl font-bold text-red-600 dark:text-red-400">{stats.offline}</p>
						</div>
					</div>
				</Card.Content>
			</Card>

			<Card>
				<Card.Content className="p-4">
					<div className="flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">
							<CheckCircle2 className="h-5 w-5" />
						</div>
						<div>
							<p className="text-sm text-gray-500 dark:text-gray-400">Tasks Done</p>
							<p className="text-xl font-bold text-gray-900 dark:text-white">
								{stats.totalTasks.toLocaleString()}
							</p>
						</div>
					</div>
				</Card.Content>
			</Card>
		</div>
	);
}

export default function Workers() {
	const [search, setSearch] = useState("");
	const [statusFilter, setStatusFilter] = useState<WorkerStatus | "all">("all");
	const [selectedWorkerId, setSelectedWorkerId] = useState<string | null>(null);

	// Build filters from search and status
	const filters: Partial<WorkerFilters> = useMemo(
		() => ({
			status: statusFilter === "all" ? undefined : statusFilter,
			search: search || undefined,
		}),
		[statusFilter, search],
	);

	const { data, isPending: isLoading, error, refetch, isFetching } = useWorkers({ filters });

	const workers = data?.items ?? [];
	const invalidateWorkers = useInvalidateWorkers();

	const handleViewDetails = (workerId: string) => {
		setSelectedWorkerId(workerId);
	};

	const handleCloseModal = () => {
		setSelectedWorkerId(null);
	};

	const handleActionPerformed = () => {
		invalidateWorkers();
	};

	if (error) {
		return (
			<div className="flex flex-col items-center justify-center py-12 text-center">
				<XCircle className="h-12 w-12 text-red-500 mb-4" />
				<h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
					Failed to load workers
				</h2>
				<p className="text-gray-500 dark:text-gray-400 mb-4">
					{error instanceof Error ? error.message : "An error occurred"}
				</p>
				<Button onPress={() => refetch()}>
					<RefreshCw className="h-4 w-4" />
					Try Again
				</Button>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<h1 className="text-2xl font-bold text-gray-900 dark:text-white">Workers</h1>
					<p className="text-gray-500 dark:text-gray-400">Monitor and manage your task workers</p>
				</div>
				<Button variant="outline" onPress={() => refetch()} isDisabled={isFetching}>
					<RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
					Refresh
				</Button>
			</div>

			{isLoading ? (
				<div className="flex items-center justify-center py-12">
					<Spinner size="lg" />
				</div>
			) : (
				<>
					{/* Stats */}
					<WorkerStats workers={workers} />

					{/* Filters */}
					<div className="flex flex-col gap-4 sm:flex-row">
						<div className="flex-1 max-w-md">
							<TextField placeholder="Search workers..." value={search} onChange={setSearch} />
						</div>

						<div className="flex gap-2">
							{(["all", "active", "idle", "offline"] as const).map((status) => (
								<Button
									key={status}
									variant={statusFilter === status ? "primary" : "outline"}
									size="sm"
									onPress={() => setStatusFilter(status)}
								>
									{status.charAt(0).toUpperCase() + status.slice(1)}
								</Button>
							))}
						</div>
					</div>

					{/* Workers Grid */}
					{workers.length === 0 ? (
						<Card>
							<Card.Content className="py-12 text-center">
								<HardDrive className="h-12 w-12 text-gray-400 mx-auto mb-4" />
								<h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">
									No workers found
								</h3>
								<p className="text-gray-500 dark:text-gray-400">
									{search || statusFilter !== "all"
										? "Try adjusting your search or filter criteria"
										: "No workers are currently registered"}
								</p>
							</Card.Content>
						</Card>
					) : (
						<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
							{workers.map((worker) => (
								<WorkerCard key={worker.id} worker={worker} onViewDetails={handleViewDetails} />
							))}
						</div>
					)}
				</>
			)}

			{/* Worker Detail Modal */}
			<WorkerDetailModal
				workerId={selectedWorkerId ?? ""}
				isOpen={selectedWorkerId !== null}
				onClose={handleCloseModal}
				onActionPerformed={handleActionPerformed}
			/>
		</div>
	);
}

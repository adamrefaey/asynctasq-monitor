import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	type Activity,
	AlertTriangle,
	ArrowDownRight,
	ArrowUpRight,
	CheckCircle2,
	Clock,
	Inbox,
	Layers,
	Pause,
	Play,
	RefreshCw,
	Trash2,
	XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Button, Card, Modal, Spinner, TextField } from "@/components/ui";
import { api } from "@/lib/api";
import type { Queue, QueueStatus } from "@/lib/types";

const statusConfig: Record<
	QueueStatus,
	{ color: "success" | "warning" | "error" | "default"; icon: typeof Activity }
> = {
	active: { color: "success", icon: Play },
	paused: { color: "warning", icon: Pause },
	draining: { color: "error", icon: ArrowDownRight },
};

function QueueStatusBadge({ status }: { status: QueueStatus }) {
	const config = statusConfig[status];
	const Icon = config.icon;

	return (
		<Badge variant={config.color} className="inline-flex items-center gap-1">
			<Icon className="h-3 w-3" />
			{status}
		</Badge>
	);
}

function ThroughputChart({ data }: { data: number[] }) {
	// Generate chart data from the array
	const chartData = useMemo(
		() =>
			data.map((value, index) => ({
				time: index,
				value,
			})),
		[data],
	);

	const trend = useMemo(() => {
		if (data.length < 2) return 0;
		const lastValue = data[data.length - 1] ?? 0;
		const prevValue = data[data.length - 2] ?? 0;
		if (prevValue === 0) return 0;
		return ((lastValue - prevValue) / prevValue) * 100;
	}, [data]);

	return (
		<div className="space-y-2">
			<div className="flex items-center justify-between">
				<span className="text-sm text-gray-500 dark:text-gray-400">Throughput (last hour)</span>
				<div
					className={`flex items-center gap-1 text-sm font-medium ${
						trend >= 0 ? "text-green-600" : "text-red-600"
					}`}
				>
					{trend >= 0 ? (
						<ArrowUpRight className="h-4 w-4" />
					) : (
						<ArrowDownRight className="h-4 w-4" />
					)}
					{Math.abs(trend).toFixed(1)}%
				</div>
			</div>
			<div className="h-16">
				<ResponsiveContainer width="100%" height="100%">
					<AreaChart data={chartData}>
						<defs>
							<linearGradient id="throughputGradient" x1="0" y1="0" x2="0" y2="1">
								<stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
								<stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
							</linearGradient>
						</defs>
						<XAxis dataKey="time" hide />
						<YAxis hide domain={["auto", "auto"]} />
						<Tooltip
							contentStyle={{
								backgroundColor: "var(--tooltip-bg, #1f2937)",
								border: "none",
								borderRadius: "0.5rem",
								color: "var(--tooltip-text, #f9fafb)",
							}}
							formatter={(value: number) => [`${value} tasks/min`, "Throughput"]}
							labelFormatter={() => ""}
						/>
						<Area
							type="monotone"
							dataKey="value"
							stroke="#3b82f6"
							strokeWidth={2}
							fill="url(#throughputGradient)"
						/>
					</AreaChart>
				</ResponsiveContainer>
			</div>
		</div>
	);
}

function QueueCard({
	queue,
	onAction,
}: {
	queue: Queue;
	onAction: (action: "pause" | "resume" | "clear", queue: Queue) => void;
}) {
	const isActive = queue.status === "active";
	const isPaused = queue.status === "paused";

	// Generate mock throughput data for visualization
	const throughputData = useMemo(() => {
		const baseValue = queue.depth > 0 ? Math.floor(queue.depth / 10) : 5;
		return Array.from({ length: 12 }, (_, i) =>
			Math.max(0, baseValue + Math.floor(Math.random() * 10) - 5 + i),
		);
	}, [queue.depth]);

	// Format average processing time
	const avgProcessingTime = useMemo(() => {
		if (queue.avg_duration_seconds !== null) {
			return `${queue.avg_duration_seconds.toFixed(2)}s`;
		}
		if (queue.avg_duration_ms !== null) {
			return `${(queue.avg_duration_ms / 1000).toFixed(2)}s`;
		}
		return "N/A";
	}, [queue.avg_duration_seconds, queue.avg_duration_ms]);

	return (
		<Card className="hover:border-gray-300 dark:hover:border-gray-600 transition-colors">
			<Card.Header>
				<div className="flex items-start justify-between">
					<div className="flex items-center gap-3">
						<div
							className={`
              flex h-10 w-10 items-center justify-center rounded-lg
              ${
								isActive
									? "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
									: "bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500"
							}
            `}
						>
							<Layers className="h-5 w-5" />
						</div>
						<div>
							<h3 className="font-semibold text-gray-900 dark:text-white">{queue.name}</h3>
							<p className="text-sm text-gray-500 dark:text-gray-400">
								{queue.workers_assigned} worker{queue.workers_assigned !== 1 ? "s" : ""} assigned
							</p>
						</div>
					</div>
					<QueueStatusBadge status={queue.status} />
				</div>
			</Card.Header>

			<Card.Content className="space-y-4">
				{/* Queue Stats */}
				<div className="grid grid-cols-3 gap-3">
					<div className="text-center rounded-lg bg-gray-50 dark:bg-gray-800/50 p-3">
						<div className="flex items-center justify-center gap-1 text-blue-600 dark:text-blue-400 mb-1">
							<Inbox className="h-4 w-4" />
						</div>
						<p className="text-lg font-bold text-gray-900 dark:text-white">
							{queue.depth.toLocaleString()}
						</p>
						<p className="text-xs text-gray-500 dark:text-gray-400">Pending</p>
					</div>

					<div className="text-center rounded-lg bg-gray-50 dark:bg-gray-800/50 p-3">
						<div className="flex items-center justify-center gap-1 text-green-600 dark:text-green-400 mb-1">
							<CheckCircle2 className="h-4 w-4" />
						</div>
						<p className="text-lg font-bold text-gray-900 dark:text-white">
							{queue.completed_total.toLocaleString()}
						</p>
						<p className="text-xs text-gray-500 dark:text-gray-400">Completed</p>
					</div>

					<div className="text-center rounded-lg bg-gray-50 dark:bg-gray-800/50 p-3">
						<div className="flex items-center justify-center gap-1 text-red-600 dark:text-red-400 mb-1">
							<XCircle className="h-4 w-4" />
						</div>
						<p className="text-lg font-bold text-gray-900 dark:text-white">
							{queue.failed_total.toLocaleString()}
						</p>
						<p className="text-xs text-gray-500 dark:text-gray-400">Failed</p>
					</div>
				</div>

				{/* Throughput Chart */}
				<ThroughputChart data={throughputData} />

				{/* Average Processing Time */}
				<div className="flex items-center justify-between text-sm">
					<span className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
						<Clock className="h-4 w-4" />
						Avg. Processing Time
					</span>
					<span className="font-medium text-gray-900 dark:text-white">{avgProcessingTime}</span>
				</div>

				{/* Actions */}
				<div className="flex gap-2 pt-2 border-t border-gray-100 dark:border-gray-700">
					{isActive ? (
						<Button
							variant="outline"
							size="sm"
							className="flex-1"
							onPress={() => onAction("pause", queue)}
						>
							<Pause className="h-4 w-4" />
							Pause
						</Button>
					) : isPaused ? (
						<Button
							variant="primary"
							size="sm"
							className="flex-1"
							onPress={() => onAction("resume", queue)}
						>
							<Play className="h-4 w-4" />
							Resume
						</Button>
					) : null}
					<Button variant="danger" size="sm" onPress={() => onAction("clear", queue)}>
						<Trash2 className="h-4 w-4" />
					</Button>
				</div>
			</Card.Content>
		</Card>
	);
}

function QueueStats({ queues }: { queues: Queue[] }) {
	const stats = useMemo(() => {
		const active = queues.filter((q) => q.status === "active").length;
		const totalDepth = queues.reduce((sum, q) => sum + q.depth, 0);
		const totalCompleted = queues.reduce((sum, q) => sum + q.completed_total, 0);
		const totalFailed = queues.reduce((sum, q) => sum + q.failed_total, 0);
		const totalWorkers = queues.reduce((sum, q) => sum + q.workers_assigned, 0);

		// Calculate average time from avg_duration_ms or avg_duration_seconds
		const avgTimes = queues
			.map((q) => {
				if (q.avg_duration_seconds !== null) return q.avg_duration_seconds;
				if (q.avg_duration_ms !== null) return q.avg_duration_ms / 1000;
				return null;
			})
			.filter((t): t is number => t !== null);
		const avgTime = avgTimes.length > 0 ? avgTimes.reduce((a, b) => a + b, 0) / avgTimes.length : 0;

		return {
			total: queues.length,
			active,
			totalDepth,
			totalCompleted,
			totalFailed,
			totalWorkers,
			avgTime,
		};
	}, [queues]);

	return (
		<div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
			<Card>
				<Card.Content className="p-4">
					<div className="flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
							<Layers className="h-5 w-5" />
						</div>
						<div>
							<p className="text-sm text-gray-500 dark:text-gray-400">{stats.active} Active</p>
							<p className="text-xl font-bold text-gray-900 dark:text-white">
								{stats.total} Queues
							</p>
						</div>
					</div>
				</Card.Content>
			</Card>

			<Card>
				<Card.Content className="p-4">
					<div className="flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400">
							<Inbox className="h-5 w-5" />
						</div>
						<div>
							<p className="text-sm text-gray-500 dark:text-gray-400">Pending</p>
							<p className="text-xl font-bold text-yellow-600 dark:text-yellow-400">
								{stats.totalDepth.toLocaleString()}
							</p>
						</div>
					</div>
				</Card.Content>
			</Card>

			<Card>
				<Card.Content className="p-4">
					<div className="flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400">
							<CheckCircle2 className="h-5 w-5" />
						</div>
						<div>
							<p className="text-sm text-gray-500 dark:text-gray-400">Completed</p>
							<p className="text-xl font-bold text-green-600 dark:text-green-400">
								{stats.totalCompleted.toLocaleString()}
							</p>
						</div>
					</div>
				</Card.Content>
			</Card>

			<Card>
				<Card.Content className="p-4">
					<div className="flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">
							<Clock className="h-5 w-5" />
						</div>
						<div>
							<p className="text-sm text-gray-500 dark:text-gray-400">Avg. Time</p>
							<p className="text-xl font-bold text-gray-900 dark:text-white">
								{stats.avgTime.toFixed(2)}s
							</p>
						</div>
					</div>
				</Card.Content>
			</Card>
		</div>
	);
}

function QueuesErrorState({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
	return (
		<div className="flex flex-col items-center justify-center py-12 text-center">
			<XCircle className="h-12 w-12 text-red-500 mb-4" />
			<h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
				Failed to load queues
			</h2>
			<p className="text-gray-500 dark:text-gray-400 mb-4">
				{error instanceof Error ? error.message : "An error occurred"}
			</p>
			<Button onPress={onRetry}>
				<RefreshCw className="h-4 w-4" />
				Try Again
			</Button>
		</div>
	);
}

function QueuesEmptyState({ hasFilters }: { hasFilters: boolean }) {
	return (
		<Card>
			<Card.Content className="py-12 text-center">
				<Layers className="h-12 w-12 text-gray-400 mx-auto mb-4" />
				<h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">No queues found</h3>
				<p className="text-gray-500 dark:text-gray-400">
					{hasFilters
						? "Try adjusting your search or filter criteria"
						: "No queues are currently configured"}
				</p>
			</Card.Content>
		</Card>
	);
}

function ConfirmActionModal({
	confirmAction,
	onClose,
	onConfirm,
	isPending,
}: {
	confirmAction: { action: "pause" | "resume" | "clear"; queue: Queue } | null;
	onClose: () => void;
	onConfirm: () => void;
	isPending: boolean;
}) {
	const getTitle = () => {
		if (confirmAction?.action === "clear") return "Clear Queue";
		if (confirmAction?.action === "pause") return "Pause Queue";
		return "Resume Queue";
	};

	const getMessage = () => {
		if (!confirmAction) return "";
		const { action, queue } = confirmAction;
		if (action === "clear") {
			return `Are you sure you want to clear all ${queue.depth.toLocaleString()} pending tasks from "${queue.name}"? This action cannot be undone.`;
		}
		if (action === "pause") {
			return `Are you sure you want to pause the queue "${queue.name}"? Workers will stop processing new tasks.`;
		}
		return `Resume processing tasks in queue "${queue.name}"?`;
	};

	return (
		<Modal isOpen={confirmAction !== null} onOpenChange={(isOpen) => !isOpen && onClose()}>
			<Modal.Header>
				<Modal.Title>{getTitle()}</Modal.Title>
			</Modal.Header>
			<Modal.Body>
				<div className="flex items-start gap-3">
					<div
						className={`
							flex h-10 w-10 items-center justify-center rounded-full shrink-0
							${confirmAction?.action === "clear" ? "bg-red-100 text-red-600" : "bg-yellow-100 text-yellow-600"}
						`}
					>
						<AlertTriangle className="h-5 w-5" />
					</div>
					<div>
						<p className="text-gray-700 dark:text-gray-300">{getMessage()}</p>
					</div>
				</div>
			</Modal.Body>
			<Modal.Footer>
				<Button variant="ghost" onPress={onClose} isDisabled={isPending}>
					Cancel
				</Button>
				<Button
					variant={confirmAction?.action === "clear" ? "danger" : "primary"}
					onPress={onConfirm}
					isDisabled={isPending}
				>
					{isPending ? <Spinner size="sm" /> : null}
					{getTitle()}
				</Button>
			</Modal.Footer>
		</Modal>
	);
}

export default function Queues() {
	const [search, setSearch] = useState("");
	const [statusFilter, setStatusFilter] = useState<QueueStatus | "all">("all");
	const [confirmAction, setConfirmAction] = useState<{
		action: "pause" | "resume" | "clear";
		queue: Queue;
	} | null>(null);

	const queryClient = useQueryClient();

	const {
		data: queuesResponse,
		isLoading,
		error,
		refetch,
		isFetching,
	} = useQuery({
		queryKey: ["queues"],
		queryFn: () => api.getQueues(),
		refetchInterval: 10000,
	});

	// Extract queues array from response
	const queues = queuesResponse?.items ?? [];

	// Mutations for queue actions
	const pauseMutation = useMutation({
		mutationFn: (queueName: string) => api.pauseQueue(queueName),
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: ["queues"] });
		},
	});

	const resumeMutation = useMutation({
		mutationFn: (queueName: string) => api.resumeQueue(queueName),
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: ["queues"] });
		},
	});

	const clearMutation = useMutation({
		mutationFn: (queueName: string) => api.clearQueue(queueName),
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: ["queues"] });
		},
	});

	const isActionPending =
		pauseMutation.isPending || resumeMutation.isPending || clearMutation.isPending;

	const filteredQueues = useMemo(() => {
		return queues.filter((queue) => {
			const matchesSearch = queue.name.toLowerCase().includes(search.toLowerCase());
			const matchesStatus = statusFilter === "all" || queue.status === statusFilter;
			return matchesSearch && matchesStatus;
		});
	}, [queues, search, statusFilter]);

	const handleAction = (action: "pause" | "resume" | "clear", queue: Queue) => {
		setConfirmAction({ action, queue });
	};

	const executeAction = async () => {
		if (!confirmAction) return;

		const { action, queue } = confirmAction;

		try {
			switch (action) {
				case "pause":
					await pauseMutation.mutateAsync(queue.name);
					break;
				case "resume":
					await resumeMutation.mutateAsync(queue.name);
					break;
				case "clear":
					await clearMutation.mutateAsync(queue.name);
					break;
			}
		} finally {
			setConfirmAction(null);
		}
	};

	if (error) {
		return <QueuesErrorState error={error} onRetry={() => refetch()} />;
	}

	const hasFilters = search !== "" || statusFilter !== "all";

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<h1 className="text-2xl font-bold text-gray-900 dark:text-white">Queues</h1>
					<p className="text-gray-500 dark:text-gray-400">Monitor and manage your task queues</p>
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
					<QueueStats queues={queues} />

					{/* Filters */}
					<div className="flex flex-col gap-4 sm:flex-row">
						<div className="flex-1 max-w-md">
							<TextField
								aria-label="Search queues"
								placeholder="Search queues..."
								value={search}
								onChange={setSearch}
							/>
						</div>

						<div className="flex gap-2">
							{(["all", "active", "paused", "draining"] as const).map((status) => (
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

					{/* Queues Grid */}
					{filteredQueues.length === 0 ? (
						<QueuesEmptyState hasFilters={hasFilters} />
					) : (
						<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
							{filteredQueues.map((queue) => (
								<QueueCard key={queue.name} queue={queue} onAction={handleAction} />
							))}
						</div>
					)}
				</>
			)}

			<ConfirmActionModal
				confirmAction={confirmAction}
				onClose={() => setConfirmAction(null)}
				onConfirm={executeAction}
				isPending={isActionPending}
			/>
		</div>
	);
}

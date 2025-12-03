import { useQuery } from "@tanstack/react-query";
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
import { fetchQueues } from "@/lib/api";
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
		const baseValue = queue.size > 0 ? Math.floor(queue.size / 10) : 5;
		return Array.from({ length: 12 }, (_, i) =>
			Math.max(0, baseValue + Math.floor(Math.random() * 10) - 5 + i),
		);
	}, [queue.size]);

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
								{queue.workers} worker{queue.workers !== 1 ? "s" : ""} assigned
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
							{queue.size.toLocaleString()}
						</p>
						<p className="text-xs text-gray-500 dark:text-gray-400">Pending</p>
					</div>

					<div className="text-center rounded-lg bg-gray-50 dark:bg-gray-800/50 p-3">
						<div className="flex items-center justify-center gap-1 text-green-600 dark:text-green-400 mb-1">
							<CheckCircle2 className="h-4 w-4" />
						</div>
						<p className="text-lg font-bold text-gray-900 dark:text-white">
							{queue.processed.toLocaleString()}
						</p>
						<p className="text-xs text-gray-500 dark:text-gray-400">Processed</p>
					</div>

					<div className="text-center rounded-lg bg-gray-50 dark:bg-gray-800/50 p-3">
						<div className="flex items-center justify-center gap-1 text-red-600 dark:text-red-400 mb-1">
							<XCircle className="h-4 w-4" />
						</div>
						<p className="text-lg font-bold text-gray-900 dark:text-white">
							{queue.failed.toLocaleString()}
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
					<span className="font-medium text-gray-900 dark:text-white">
						{queue.avgProcessingTime.toFixed(2)}s
					</span>
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
		const totalSize = queues.reduce((sum, q) => sum + q.size, 0);
		const totalProcessed = queues.reduce((sum, q) => sum + q.processed, 0);
		const totalFailed = queues.reduce((sum, q) => sum + q.failed, 0);
		const totalWorkers = queues.reduce((sum, q) => sum + q.workers, 0);
		const avgTime =
			queues.length > 0
				? queues.reduce((sum, q) => sum + q.avgProcessingTime, 0) / queues.length
				: 0;

		return {
			total: queues.length,
			active,
			totalSize,
			totalProcessed,
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
								{stats.totalSize.toLocaleString()}
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
							<p className="text-sm text-gray-500 dark:text-gray-400">Processed</p>
							<p className="text-xl font-bold text-green-600 dark:text-green-400">
								{stats.totalProcessed.toLocaleString()}
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
}: {
	confirmAction: { action: "pause" | "resume" | "clear"; queue: Queue } | null;
	onClose: () => void;
	onConfirm: () => void;
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
			return `Are you sure you want to clear all ${queue.size.toLocaleString()} pending tasks from "${queue.name}"? This action cannot be undone.`;
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
				<Button variant="ghost" onPress={onClose}>
					Cancel
				</Button>
				<Button
					variant={confirmAction?.action === "clear" ? "danger" : "primary"}
					onPress={onConfirm}
				>
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

	const {
		data: queues = [],
		isLoading,
		error,
		refetch,
		isFetching,
	} = useQuery({
		queryKey: ["queues"],
		queryFn: fetchQueues,
		refetchInterval: 10000,
	});

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

		// TODO: Implement API calls for pause/resume/clear
		// When implementing, use:
		// await api.queues.pause(confirmAction.queue.name)
		// await api.queues.resume(confirmAction.queue.name)
		// await api.queues.clear(confirmAction.queue.name)

		setConfirmAction(null);
		void refetch();
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
							<TextField placeholder="Search queues..." value={search} onChange={setSearch} />
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
			/>
		</div>
	);
}

/**
 * Metrics page with time-series charts and analytics.
 * Uses Recharts for visualization following React best practices.
 */

import { useQuery } from "@tanstack/react-query";
import { XCircle } from "lucide-react";
import { useState } from "react";
import {
	Area,
	AreaChart,
	Bar,
	BarChart,
	CartesianGrid,
	Legend,
	Line,
	LineChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
	LoadingOverlay,
	Select,
	SelectItem,
} from "@/components/ui";
import { api } from "@/lib/api";
import type { MetricsSummary, ThroughputDataPoint } from "@/lib/types";

/** Time range options matching backend API */
const TIME_RANGES = [
	{ value: "1h", label: "Last hour" },
	{ value: "6h", label: "Last 6 hours" },
	{ value: "24h", label: "Last 24 hours" },
	{ value: "7d", label: "Last 7 days" },
	{ value: "30d", label: "Last 30 days" },
] as const;

/** Chart color palette matching tailwind theme */
const CHART_COLORS = {
	completed: "#10b981", // emerald-500
	failed: "#ef4444", // red-500
	pending: "#f59e0b", // amber-500
	running: "#3b82f6", // blue-500
	successRate: "#3b82f6", // blue-500
	queue1: "#3b82f6",
	queue2: "#10b981",
	queue3: "#f59e0b",
	queue4: "#ef4444",
	queue5: "#8b5cf6",
} as const;

const QUEUE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

/**
 * Format timestamp for chart axis labels.
 */
function formatAxisTimestamp(timestamp: string): string {
	const date = new Date(timestamp);
	return date.toLocaleTimeString(undefined, {
		hour: "2-digit",
		minute: "2-digit",
	});
}

/**
 * Payload entry from Recharts Tooltip.
 */
interface TooltipEntry {
	name?: string;
	value?: number;
	color?: string;
	dataKey?: string;
}

/**
 * Props for custom tooltip components.
 */
interface CustomTooltipProps {
	active?: boolean;
	payload?: TooltipEntry[];
	label?: string;
}

/**
 * Custom tooltip for throughput chart.
 */
function ThroughputTooltip({ active, payload, label }: CustomTooltipProps): React.ReactNode {
	if (!active || !payload || payload.length === 0) return null;

	return (
		<div className="rounded-lg border border-zinc-200 bg-white p-3 shadow-lg dark:border-zinc-700 dark:bg-zinc-800">
			<p className="mb-2 text-xs text-zinc-500 dark:text-zinc-400">{label}</p>
			{payload.map((entry) => (
				<p key={entry.name} className="text-sm" style={{ color: entry.color }}>
					{entry.name}: {entry.value?.toLocaleString()}
				</p>
			))}
		</div>
	);
}

/**
 * Custom tooltip for success rate chart.
 */
function SuccessRateTooltip({ active, payload, label }: CustomTooltipProps): React.ReactNode {
	if (!active || !payload || payload.length === 0) return null;

	return (
		<div className="rounded-lg border border-zinc-200 bg-white p-3 shadow-lg dark:border-zinc-700 dark:bg-zinc-800">
			<p className="mb-2 text-xs text-zinc-500 dark:text-zinc-400">{label}</p>
			{payload.map((entry) => (
				<p key={entry.name} className="text-sm" style={{ color: entry.color }}>
					{entry.name}:{" "}
					{typeof entry.value === "number" ? `${entry.value.toFixed(1)}%` : entry.value}
				</p>
			))}
		</div>
	);
}

/**
 * Duration percentile stat card.
 */
function PercentileStat({
	label,
	value,
}: {
	label: string;
	value: number | null | undefined;
}): React.ReactNode {
	return (
		<div className="rounded-lg bg-zinc-100 p-4 dark:bg-zinc-800">
			<div className="text-sm text-zinc-500 dark:text-zinc-400">{label}</div>
			<div className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
				{value != null ? `${value.toLocaleString()}ms` : "—"}
			</div>
		</div>
	);
}

/**
 * Compute success rate for throughput data points.
 */
function computeSuccessRates(data: ThroughputDataPoint[]): ThroughputDataPoint[] {
	return data.map((point) => {
		const total = point.completed + point.failed;
		const successRate = total > 0 ? (point.completed / total) * 100 : 100;
		return { ...point, successRate };
	});
}

/**
 * Status breakdown bar chart data.
 */
interface StatusBarData {
	name: string;
	value: number;
	fill: string;
}

export default function MetricsPage(): React.ReactNode {
	const [timeRange, setTimeRange] = useState("24h");

	const { data, isLoading, error } = useQuery<MetricsSummary>({
		queryKey: ["metrics", "summary", timeRange],
		queryFn: () => api.getMetricsSummary(timeRange),
		refetchInterval: 30000, // Refresh every 30 seconds
	});

	if (isLoading) {
		return <LoadingOverlay label="Loading metrics..." />;
	}

	if (error) {
		return (
			<div className="flex flex-col items-center justify-center gap-4 p-12">
				<XCircle className="h-12 w-12 text-red-500" />
				<p className="text-lg font-medium text-zinc-900 dark:text-zinc-100">
					Failed to load metrics
				</p>
				<p className="text-sm text-zinc-500">
					{error instanceof Error ? error.message : "An error occurred"}
				</p>
			</div>
		);
	}

	// Process data for charts
	const throughputData = computeSuccessRates(data?.throughput ?? []);
	const statusBreakdownData: StatusBarData[] = [
		{
			name: "Pending",
			value: data?.status_breakdown?.pending ?? 0,
			fill: CHART_COLORS.pending,
		},
		{
			name: "Running",
			value: data?.status_breakdown?.running ?? 0,
			fill: CHART_COLORS.running,
		},
		{
			name: "Completed",
			value: data?.status_breakdown?.completed ?? 0,
			fill: CHART_COLORS.completed,
		},
		{
			name: "Failed",
			value: data?.status_breakdown?.failed ?? 0,
			fill: CHART_COLORS.failed,
		},
	];

	return (
		<div className="space-y-6">
			{/* Header with time range selector */}
			<div className="flex items-center justify-between">
				<h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
					Metrics & Analytics
				</h1>
				<Select
					aria-label="Time range"
					selectedKey={timeRange}
					onSelectionChange={(key) => setTimeRange(key as string)}
				>
					{TIME_RANGES.map((range) => (
						<SelectItem key={range.value} id={range.value}>
							{range.label}
						</SelectItem>
					))}
				</Select>
			</div>

			{/* Charts grid */}
			<div className="grid gap-6 lg:grid-cols-2">
				{/* Task Throughput - Stacked Area Chart */}
				<Card>
					<CardHeader>
						<CardTitle>Task Throughput</CardTitle>
					</CardHeader>
					<CardContent className="h-72">
						<ResponsiveContainer width="100%" height="100%">
							<AreaChart data={throughputData}>
								<defs>
									<linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
										<stop offset="5%" stopColor={CHART_COLORS.completed} stopOpacity={0.8} />
										<stop offset="95%" stopColor={CHART_COLORS.completed} stopOpacity={0.1} />
									</linearGradient>
									<linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
										<stop offset="5%" stopColor={CHART_COLORS.failed} stopOpacity={0.8} />
										<stop offset="95%" stopColor={CHART_COLORS.failed} stopOpacity={0.1} />
									</linearGradient>
								</defs>
								<CartesianGrid
									strokeDasharray="3 3"
									className="stroke-zinc-200 dark:stroke-zinc-700"
								/>
								<XAxis
									dataKey="timestamp"
									tickFormatter={formatAxisTimestamp}
									tick={{ fontSize: 12 }}
									className="fill-zinc-500 dark:fill-zinc-400"
								/>
								<YAxis tick={{ fontSize: 12 }} className="fill-zinc-500 dark:fill-zinc-400" />
								<Tooltip content={<ThroughputTooltip />} />
								<Legend />
								<Area
									type="monotone"
									dataKey="completed"
									name="Completed"
									stackId="1"
									stroke={CHART_COLORS.completed}
									fill="url(#colorCompleted)"
								/>
								<Area
									type="monotone"
									dataKey="failed"
									name="Failed"
									stackId="1"
									stroke={CHART_COLORS.failed}
									fill="url(#colorFailed)"
								/>
							</AreaChart>
						</ResponsiveContainer>
					</CardContent>
				</Card>

				{/* Success Rate Over Time - Line Chart */}
				<Card>
					<CardHeader>
						<CardTitle>Success Rate</CardTitle>
					</CardHeader>
					<CardContent className="h-72">
						<ResponsiveContainer width="100%" height="100%">
							<LineChart data={throughputData}>
								<CartesianGrid
									strokeDasharray="3 3"
									className="stroke-zinc-200 dark:stroke-zinc-700"
								/>
								<XAxis
									dataKey="timestamp"
									tickFormatter={formatAxisTimestamp}
									tick={{ fontSize: 12 }}
									className="fill-zinc-500 dark:fill-zinc-400"
								/>
								<YAxis
									domain={[0, 100]}
									tick={{ fontSize: 12 }}
									tickFormatter={(value: number) => `${value}%`}
									className="fill-zinc-500 dark:fill-zinc-400"
								/>
								<Tooltip content={<SuccessRateTooltip />} />
								<Line
									type="monotone"
									dataKey="successRate"
									name="Success Rate"
									stroke={CHART_COLORS.successRate}
									strokeWidth={2}
									dot={false}
									activeDot={{ r: 4, strokeWidth: 2 }}
								/>
							</LineChart>
						</ResponsiveContainer>
					</CardContent>
				</Card>

				{/* Status Breakdown - Bar Chart */}
				<Card>
					<CardHeader>
						<CardTitle>Status Breakdown</CardTitle>
					</CardHeader>
					<CardContent className="h-72">
						<ResponsiveContainer width="100%" height="100%">
							<BarChart data={statusBreakdownData}>
								<CartesianGrid
									strokeDasharray="3 3"
									className="stroke-zinc-200 dark:stroke-zinc-700"
								/>
								<XAxis
									dataKey="name"
									tick={{ fontSize: 12 }}
									className="fill-zinc-500 dark:fill-zinc-400"
								/>
								<YAxis tick={{ fontSize: 12 }} className="fill-zinc-500 dark:fill-zinc-400" />
								<Tooltip
									content={({ active, payload }) => {
										if (!active || !payload || payload.length === 0) return null;
										const data = payload[0]?.payload as StatusBarData;
										return (
											<div className="rounded-lg border border-zinc-200 bg-white p-3 shadow-lg dark:border-zinc-700 dark:bg-zinc-800">
												<p className="text-sm font-medium" style={{ color: data.fill }}>
													{data.name}: {data.value.toLocaleString()}
												</p>
											</div>
										);
									}}
								/>
								<Bar dataKey="value" name="Tasks" radius={[4, 4, 0, 0]} />
							</BarChart>
						</ResponsiveContainer>
					</CardContent>
				</Card>

				{/* Queue Depth Over Time - Multi-Line Chart */}
				<Card>
					<CardHeader>
						<CardTitle>Queue Depth</CardTitle>
					</CardHeader>
					<CardContent className="h-72">
						{data?.queue_depth && data.queue_depth.length > 0 ? (
							<ResponsiveContainer width="100%" height="100%">
								<LineChart data={data.queue_depth}>
									<CartesianGrid
										strokeDasharray="3 3"
										className="stroke-zinc-200 dark:stroke-zinc-700"
									/>
									<XAxis
										dataKey="timestamp"
										tickFormatter={formatAxisTimestamp}
										tick={{ fontSize: 12 }}
										className="fill-zinc-500 dark:fill-zinc-400"
									/>
									<YAxis tick={{ fontSize: 12 }} className="fill-zinc-500 dark:fill-zinc-400" />
									<Tooltip />
									<Legend />
									{(data.queues ?? []).map((queue, index) => (
										<Line
											key={queue}
											type="monotone"
											dataKey={queue}
											name={queue}
											stroke={QUEUE_COLORS[index % QUEUE_COLORS.length]}
											strokeWidth={2}
											dot={false}
											activeDot={{ r: 4 }}
										/>
									))}
								</LineChart>
							</ResponsiveContainer>
						) : (
							<div className="flex h-full items-center justify-center">
								<p className="text-sm text-zinc-500 dark:text-zinc-400">
									No queue depth data available
								</p>
							</div>
						)}
					</CardContent>
				</Card>
			</div>

			{/* Duration Percentiles Summary */}
			<Card>
				<CardHeader>
					<CardTitle>Duration Percentiles</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
						<PercentileStat label="Average" value={data?.duration?.avg_ms} />
						<PercentileStat label="P50 (Median)" value={data?.duration?.p50_ms} />
						<PercentileStat label="P95" value={data?.duration?.p95_ms} />
						<PercentileStat label="P99" value={data?.duration?.p99_ms} />
					</div>
				</CardContent>
			</Card>
		</div>
	);
}

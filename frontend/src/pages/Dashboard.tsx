/**
 * Dashboard page with key metrics and overview.
 */

import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, Clock, TrendingUp, XCircle } from "lucide-react";
import {
	Badge,
	Card,
	CardContent,
	CardHeader,
	CardTitle,
	getTaskStatusBadgeVariant,
	LoadingOverlay,
} from "@/components/ui";
import { api } from "@/lib/api";
import type { DashboardSummary, Task } from "@/lib/types";

interface StatCardProps {
	title: string;
	value: string | number;
	icon: React.ReactNode;
	trend?: {
		value: number;
		label: string;
	};
	className?: string;
}

function StatCard({ title, value, icon, trend, className = "" }: StatCardProps): React.ReactNode {
	return (
		<Card className={className}>
			<CardContent className="p-6">
				<div className="flex items-start justify-between">
					<div className="flex-1">
						<p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">{title}</p>
						<p className="mt-2 text-3xl font-semibold text-zinc-900 dark:text-zinc-100">
							{typeof value === "number" ? value.toLocaleString() : value}
						</p>
						{trend && (
							<div className="mt-2 flex items-center gap-1">
								<TrendingUp
									className={`h-4 w-4 ${trend.value >= 0 ? "text-emerald-500" : "text-red-500"}`}
								/>
								<span
									className={`text-sm font-medium ${trend.value >= 0 ? "text-emerald-600" : "text-red-600"}`}
								>
									{trend.value >= 0 ? "+" : ""}
									{trend.value}%
								</span>
								<span className="text-sm text-zinc-500 dark:text-zinc-400">{trend.label}</span>
							</div>
						)}
					</div>
					<div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-900/30">{icon}</div>
				</div>
			</CardContent>
		</Card>
	);
}

function RecentActivityItem({ task }: { task: Task }): React.ReactNode {
	return (
		<div className="flex items-center justify-between py-3">
			<div className="flex items-center gap-3">
				<div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800">
					<Activity className="h-4 w-4 text-zinc-600 dark:text-zinc-400" />
				</div>
				<div>
					<p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{task.name}</p>
					<p className="text-xs text-zinc-500 dark:text-zinc-400">{task.queue}</p>
				</div>
			</div>
			<Badge variant={getTaskStatusBadgeVariant(task.status)} dot>
				{task.status}
			</Badge>
		</div>
	);
}

export default function DashboardPage(): React.ReactNode {
	const { data, isLoading, error } = useQuery<DashboardSummary>({
		queryKey: ["dashboard"],
		queryFn: api.getDashboardSummary,
		refetchInterval: 5000, // Refresh every 5 seconds
	});

	if (isLoading) {
		return <LoadingOverlay label="Loading dashboard..." />;
	}

	if (error) {
		return (
			<div className="flex flex-col items-center justify-center gap-4 p-12">
				<XCircle className="h-12 w-12 text-red-500" />
				<p className="text-lg font-medium text-zinc-900 dark:text-zinc-100">
					Failed to load dashboard
				</p>
				<p className="text-sm text-zinc-500">
					{error instanceof Error ? error.message : "An error occurred"}
				</p>
			</div>
		);
	}

	// Show placeholder data if no data available
	const summary: DashboardSummary = data ?? {
		total_tasks: 0,
		running_tasks: 0,
		pending_tasks: 0,
		completed_tasks: 0,
		failed_tasks: 0,
		success_rate: 0,
		queues: [],
		workers: [],
		recent_activity: [],
	};

	return (
		<div className="space-y-6">
			{/* Stats grid */}
			<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
				<StatCard
					title="Total Tasks"
					value={summary.total_tasks}
					icon={<Activity className="h-6 w-6 text-blue-600" />}
				/>
				<StatCard
					title="Running"
					value={summary.running_tasks}
					icon={<Clock className="h-6 w-6 text-cyan-600" />}
				/>
				<StatCard
					title="Success Rate"
					value={`${summary.success_rate.toFixed(1)}%`}
					icon={<CheckCircle2 className="h-6 w-6 text-emerald-600" />}
				/>
				<StatCard
					title="Failed"
					value={summary.failed_tasks}
					icon={<XCircle className="h-6 w-6 text-red-600" />}
				/>
			</div>

			{/* Main content grid */}
			<div className="grid gap-6 lg:grid-cols-3">
				{/* Recent Activity */}
				<Card className="lg:col-span-2">
					<CardHeader>
						<CardTitle>Recent Activity</CardTitle>
					</CardHeader>
					<CardContent>
						{summary.recent_activity.length > 0 ? (
							<div className="divide-y divide-zinc-200 dark:divide-zinc-800">
								{summary.recent_activity.slice(0, 10).map((task) => (
									<RecentActivityItem key={task.id} task={task} />
								))}
							</div>
						) : (
							<p className="py-8 text-center text-sm text-zinc-500">No recent activity</p>
						)}
					</CardContent>
				</Card>

				{/* Queue Health */}
				<Card>
					<CardHeader>
						<CardTitle>Queue Health</CardTitle>
					</CardHeader>
					<CardContent>
						{summary.queues.length > 0 ? (
							<div className="space-y-4">
								{summary.queues.map((queue) => (
									<div key={queue.name}>
										<div className="flex items-center justify-between text-sm">
											<span className="font-medium text-zinc-900 dark:text-zinc-100">
												{queue.name}
											</span>
											<span className="text-zinc-500 dark:text-zinc-400">
												{queue.depth} pending
											</span>
										</div>
										<div className="mt-1 h-2 rounded-full bg-zinc-200 dark:bg-zinc-700">
											<div
												className="h-2 rounded-full bg-blue-600"
												style={{
													width: `${Math.min((queue.processing / Math.max(queue.depth + queue.processing, 1)) * 100, 100)}%`,
												}}
											/>
										</div>
									</div>
								))}
							</div>
						) : (
							<p className="py-8 text-center text-sm text-zinc-500">No queues configured</p>
						)}
					</CardContent>
				</Card>
			</div>
		</div>
	);
}

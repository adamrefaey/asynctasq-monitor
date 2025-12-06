/**
 * Tasks list page with filtering, search, and actions.
 *
 * Uses TanStack Query v5 hooks and React Table for data management.
 * Includes TaskDetail modal for viewing complete task information.
 */

import {
	createColumnHelper,
	flexRender,
	getCoreRowModel,
	getSortedRowModel,
	type SortingState,
	useReactTable,
} from "@tanstack/react-table";
import { format, formatDistanceToNow } from "date-fns";
import {
	ArrowUpDown,
	ChevronLeft,
	ChevronRight,
	Eye,
	RefreshCw,
	Search,
	Trash2,
} from "lucide-react";
import { type ReactNode, useMemo, useState } from "react";
import { TaskDetailModal } from "@/components/TaskDetailModal";
import {
	Badge,
	Button,
	Card,
	CardContent,
	getTaskStatusBadgeVariant,
	LoadingOverlay,
	Select,
	SelectItem,
} from "@/components/ui";
import { useDeleteTask, usePrefetchTask, useRetryTask, useTasks } from "@/hooks/useTasks";
import type { Task, TaskFilters, TaskStatus } from "@/lib/types";

const columnHelper = createColumnHelper<Task>();

const statusOptions: Array<{ value: TaskStatus | "all"; label: string }> = [
	{ value: "all", label: "All statuses" },
	{ value: "pending", label: "Pending" },
	{ value: "running", label: "Running" },
	{ value: "completed", label: "Completed" },
	{ value: "failed", label: "Failed" },
	{ value: "retrying", label: "Retrying" },
	{ value: "cancelled", label: "Cancelled" },
];

function formatDuration(value: number | null): string {
	if (value === null) return "—";
	return value < 1000 ? `${value}ms` : `${(value / 1000).toFixed(2)}s`;
}

interface TaskFiltersBarProps {
	searchQuery: string;
	onSearchChange: (value: string) => void;
	statusFilter: TaskStatus | "all";
	onStatusChange: (value: TaskStatus | "all") => void;
	queueFilter: string;
	onQueueChange: (value: string) => void;
	onClearFilters: () => void;
	onRefresh: () => void;
	isPending: boolean;
	hasActiveFilters: boolean;
}

function TaskFiltersBar({
	searchQuery,
	onSearchChange,
	statusFilter,
	onStatusChange,
	queueFilter,
	onQueueChange,
	onClearFilters,
	onRefresh,
	isPending,
	hasActiveFilters,
}: TaskFiltersBarProps): ReactNode {
	return (
		<Card padding="sm">
			<CardContent className="flex flex-wrap items-center gap-4 p-4">
				{/* Search */}
				<div className="relative flex-1 min-w-[200px]">
					<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
					<input
						aria-label="Search tasks by name or ID"
						type="search"
						placeholder="Search tasks by name or ID..."
						value={searchQuery}
						onChange={(e) => onSearchChange(e.target.value)}
						className="h-10 w-full rounded-lg border border-zinc-300 bg-white pl-10 pr-3 text-sm outline-none placeholder:text-zinc-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
					/>
				</div>

				{/* Status filter */}
				<Select<{ value: string; label: string }>
					aria-label="Filter by status"
					selectedKey={statusFilter}
					onSelectionChange={(key) => onStatusChange(key as TaskStatus | "all")}
					placeholder="Filter by status"
					className="w-40"
				>
					{statusOptions.map((option) => (
						<SelectItem key={option.value} id={option.value}>
							{option.label}
						</SelectItem>
					))}
				</Select>

				{/* Queue filter */}
				<div className="relative">
					<input
						aria-label="Filter by queue name"
						type="text"
						placeholder="Queue name..."
						value={queueFilter}
						onChange={(e) => onQueueChange(e.target.value)}
						className="h-10 w-40 rounded-lg border border-zinc-300 bg-white px-3 text-sm outline-none placeholder:text-zinc-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
					/>
					{queueFilter && (
						<button
							type="button"
							className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
							onClick={() => onQueueChange("")}
							aria-label="Clear queue filter"
						>
							×
						</button>
					)}
				</div>

				{/* Clear filters */}
				{hasActiveFilters && (
					<Button variant="ghost" size="sm" onPress={onClearFilters}>
						Clear filters
					</Button>
				)}

				{/* Refresh button */}
				<Button variant="secondary" size="md" onPress={onRefresh} isDisabled={isPending}>
					<RefreshCw className={`h-4 w-4 ${isPending ? "animate-spin" : ""}`} />
					Refresh
				</Button>
			</CardContent>
		</Card>
	);
}

interface TaskActionsProps {
	task: Task;
	onView: () => void;
	onRetry: () => void;
	onDelete: () => void;
	isRetrying: boolean;
	isDeleting: boolean;
}

function TaskActions({
	task,
	onView,
	onRetry,
	onDelete,
	isRetrying,
	isDeleting,
}: TaskActionsProps): ReactNode {
	const canRetry = task.status === "failed" || task.status === "cancelled";
	const canDelete = task.status !== "running";

	return (
		<div className="flex items-center justify-end gap-1">
			<Button variant="ghost" size="icon-sm" onPress={onView} aria-label="View task details">
				<Eye className="h-4 w-4" />
			</Button>
			{canRetry && (
				<Button
					variant="ghost"
					size="icon-sm"
					onPress={onRetry}
					isDisabled={isRetrying}
					aria-label="Retry task"
				>
					<RefreshCw className="h-4 w-4" />
				</Button>
			)}
			{canDelete && (
				<Button
					variant="ghost"
					size="icon-sm"
					onPress={onDelete}
					isDisabled={isDeleting}
					aria-label="Delete task"
				>
					<Trash2 className="h-4 w-4" />
				</Button>
			)}
		</div>
	);
}

function createTaskColumns(
	setQueueFilter: (queue: string) => void,
	setSelectedTaskId: (id: string) => void,
	retryTask: (params: { taskId: string }) => void,
	deleteTask: (params: { taskId: string }) => void,
	isRetrying: boolean,
	isDeleting: boolean,
) {
	return [
		columnHelper.accessor("name", {
			header: ({ column }) => (
				<button
					type="button"
					className="flex items-center gap-1 font-medium"
					onClick={() => column.toggleSorting()}
				>
					Name
					<ArrowUpDown className="h-4 w-4" />
				</button>
			),
			cell: (info) => (
				<div className="font-medium text-zinc-900 dark:text-zinc-100">{info.getValue()}</div>
			),
		}),
		columnHelper.accessor("id", {
			header: "ID",
			cell: (info) => (
				<code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs dark:bg-zinc-800">
					{info.getValue().slice(0, 8)}...
				</code>
			),
		}),
		columnHelper.accessor("queue", {
			header: "Queue",
			cell: (info) => (
				<button
					type="button"
					className="text-zinc-600 dark:text-zinc-400 hover:text-blue-600 dark:hover:text-blue-400 hover:underline cursor-pointer"
					onClick={() => setQueueFilter(info.getValue())}
				>
					{info.getValue()}
				</button>
			),
		}),
		columnHelper.accessor("status", {
			header: "Status",
			cell: (info) => (
				<Badge variant={getTaskStatusBadgeVariant(info.getValue())} dot>
					{info.getValue()}
				</Badge>
			),
		}),
		columnHelper.accessor("enqueued_at", {
			header: ({ column }) => (
				<button
					type="button"
					className="flex items-center gap-1 font-medium"
					onClick={() => column.toggleSorting()}
				>
					Enqueued
					<ArrowUpDown className="h-4 w-4" />
				</button>
			),
			cell: (info) => (
				<span
					className="text-zinc-600 dark:text-zinc-400"
					title={format(new Date(info.getValue()), "PPpp")}
				>
					{formatDistanceToNow(new Date(info.getValue()), { addSuffix: true })}
				</span>
			),
		}),
		columnHelper.accessor("duration_ms", {
			header: "Duration",
			cell: (info) => {
				const value = info.getValue();
				return <span className="text-zinc-600 dark:text-zinc-400">{formatDuration(value)}</span>;
			},
		}),
		columnHelper.accessor("attempt", {
			header: "Attempts",
			cell: (info) => (
				<span className="text-zinc-600 dark:text-zinc-400">
					{info.getValue()}/{info.row.original.max_retries}
				</span>
			),
		}),
		columnHelper.display({
			id: "actions",
			header: "",
			cell: (info) => {
				const task = info.row.original;
				return (
					<TaskActions
						task={task}
						onView={() => setSelectedTaskId(task.id)}
						onRetry={() => retryTask({ taskId: task.id })}
						onDelete={() => deleteTask({ taskId: task.id })}
						isRetrying={isRetrying}
						isDeleting={isDeleting}
					/>
				);
			},
		}),
	];
}

export default function TasksPage(): ReactNode {
	// Filter state
	const [searchQuery, setSearchQuery] = useState("");
	const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all");
	const [queueFilter, setQueueFilter] = useState("");

	// Pagination state
	const [page, setPage] = useState(0);
	const [pageSize] = useState(50);

	// Sorting state
	const [sorting, setSorting] = useState<SortingState>([]);

	// Modal state
	const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

	// Build filters object
	const filters: Partial<TaskFilters> = useMemo(
		() => ({
			status: statusFilter === "all" ? undefined : statusFilter,
			queue: queueFilter || undefined,
			search: searchQuery || undefined,
		}),
		[statusFilter, queueFilter, searchQuery],
	);

	// Fetch tasks using our custom hook
	const { data, isPending, error, refetch } = useTasks({
		filters,
		limit: pageSize,
		offset: page * pageSize,
	});

	// Mutations using our custom hooks
	const { mutate: retryTask, isPending: isRetrying } = useRetryTask();
	const { mutate: deleteTask, isPending: isDeleting } = useDeleteTask();
	const prefetchTask = usePrefetchTask();

	// Table columns
	const columns = useMemo(
		() =>
			createTaskColumns(
				setQueueFilter,
				setSelectedTaskId,
				retryTask,
				deleteTask,
				isRetrying,
				isDeleting,
			),
		[retryTask, deleteTask, isRetrying, isDeleting],
	);

	// Table instance
	const table = useReactTable({
		data: data?.items ?? [],
		columns,
		getCoreRowModel: getCoreRowModel(),
		getSortedRowModel: getSortedRowModel(),
		onSortingChange: setSorting,
		state: {
			sorting,
		},
		manualPagination: true,
		pageCount: Math.ceil((data?.total ?? 0) / pageSize),
	});

	const totalPages = Math.ceil((data?.total ?? 0) / pageSize);

	// Handle clearing filters
	const handleClearFilters = () => {
		setSearchQuery("");
		setStatusFilter("all");
		setQueueFilter("");
		setPage(0);
	};

	const hasActiveFilters = Boolean(searchQuery || statusFilter !== "all" || queueFilter);

	if (error) {
		return (
			<Card>
				<CardContent className="flex flex-col items-center justify-center gap-4 py-12">
					<p className="text-lg font-medium text-zinc-900 dark:text-zinc-100">
						Failed to load tasks
					</p>
					<p className="text-sm text-zinc-500">
						{error instanceof Error ? error.message : "An error occurred"}
					</p>
					<Button variant="secondary" onPress={() => refetch()}>
						Try again
					</Button>
				</CardContent>
			</Card>
		);
	}

	const handleSearchChange = (value: string) => {
		setSearchQuery(value);
		setPage(0);
	};

	const handleStatusChange = (value: TaskStatus | "all") => {
		setStatusFilter(value);
		setPage(0);
	};

	const handleQueueChange = (value: string) => {
		setQueueFilter(value);
		setPage(0);
	};

	return (
		<div className="space-y-4">
			{/* Filters */}
			<TaskFiltersBar
				searchQuery={searchQuery}
				onSearchChange={handleSearchChange}
				statusFilter={statusFilter}
				onStatusChange={handleStatusChange}
				queueFilter={queueFilter}
				onQueueChange={handleQueueChange}
				onClearFilters={handleClearFilters}
				onRefresh={() => refetch()}
				isPending={isPending}
				hasActiveFilters={hasActiveFilters}
			/>

			{/* Tasks table */}
			<Card padding="none">
				{isPending && !data ? (
					<LoadingOverlay label="Loading tasks..." />
				) : (
					<>
						<div className="overflow-x-auto">
							<table className="w-full">
								<thead className="border-b border-zinc-200 dark:border-zinc-800">
									{table.getHeaderGroups().map((headerGroup) => (
										<tr key={headerGroup.id}>
											{headerGroup.headers.map((header) => (
												<th
													key={header.id}
													className="px-4 py-3 text-left text-sm font-medium text-zinc-500 dark:text-zinc-400"
												>
													{header.isPlaceholder
														? null
														: flexRender(header.column.columnDef.header, header.getContext())}
												</th>
											))}
										</tr>
									))}
								</thead>
								<tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
									{table.getRowModel().rows.length === 0 ? (
										<tr>
											<td
												colSpan={columns.length}
												className="py-12 text-center text-sm text-zinc-500"
											>
												{hasActiveFilters ? "No tasks match your filters" : "No tasks found"}
											</td>
										</tr>
									) : (
										table.getRowModel().rows.map((row) => (
											<tr
												key={row.id}
												className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50 cursor-pointer"
												onClick={() => setSelectedTaskId(row.original.id)}
												onMouseEnter={() => prefetchTask(row.original.id)}
											>
												{row.getVisibleCells().map((cell) => (
													<td key={cell.id} className="px-4 py-3 text-sm">
														{flexRender(cell.column.columnDef.cell, cell.getContext())}
													</td>
												))}
											</tr>
										))
									)}
								</tbody>
							</table>
						</div>

						{/* Pagination */}
						<div className="flex items-center justify-between border-t border-zinc-200 px-4 py-3 dark:border-zinc-800">
							<div className="text-sm text-zinc-500 dark:text-zinc-400">
								Showing{" "}
								<span className="font-medium">
									{data?.total === 0 ? 0 : page * pageSize + 1}-
									{Math.min((page + 1) * pageSize, data?.total ?? 0)}
								</span>{" "}
								of <span className="font-medium">{data?.total ?? 0}</span> tasks
							</div>
							<div className="flex items-center gap-2">
								<Button
									variant="outline"
									size="sm"
									onPress={() => setPage((p) => Math.max(0, p - 1))}
									isDisabled={page === 0}
								>
									<ChevronLeft className="h-4 w-4" />
									Previous
								</Button>
								<span className="text-sm text-zinc-500">
									Page {page + 1} of {Math.max(1, totalPages)}
								</span>
								<Button
									variant="outline"
									size="sm"
									onPress={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
									isDisabled={page >= totalPages - 1}
								>
									Next
									<ChevronRight className="h-4 w-4" />
								</Button>
							</div>
						</div>
					</>
				)}
			</Card>

			{/* Task Detail Modal */}
			{selectedTaskId && (
				<TaskDetailModal
					taskId={selectedTaskId}
					isOpen={selectedTaskId !== null}
					onClose={() => setSelectedTaskId(null)}
					onDeleted={() => {
						// Handled by hook - refetch happens automatically
					}}
					onRetried={() => {
						// Handled by hook - refetch happens automatically
					}}
				/>
			)}
		</div>
	);
}

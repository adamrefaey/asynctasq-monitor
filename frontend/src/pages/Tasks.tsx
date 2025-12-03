/**
 * Tasks list page with filtering, search, and actions.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	createColumnHelper,
	flexRender,
	getCoreRowModel,
	getSortedRowModel,
	type SortingState,
	useReactTable,
} from "@tanstack/react-table";
import { format, formatDistanceToNow } from "date-fns";
import { ArrowUpDown, ChevronLeft, ChevronRight, RefreshCw, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
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
import { api } from "@/lib/api";
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

export default function TasksPage(): React.ReactNode {
	const queryClient = useQueryClient();

	// Filter state
	const [searchQuery, setSearchQuery] = useState("");
	const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all");
	const [queueFilter, setQueueFilter] = useState("");

	// Pagination state
	const [page, setPage] = useState(0);
	const [pageSize] = useState(50);

	// Sorting state
	const [sorting, setSorting] = useState<SortingState>([]);

	// Build filters object
	const filters: Partial<TaskFilters> = useMemo(
		() => ({
			status: statusFilter === "all" ? undefined : statusFilter,
			queue: queueFilter || undefined,
			search: searchQuery || undefined,
		}),
		[statusFilter, queueFilter, searchQuery],
	);

	// Fetch tasks
	const { data, isLoading, error, refetch } = useQuery({
		queryKey: ["tasks", filters, page, pageSize],
		queryFn: () => api.getTasks(filters, pageSize, page * pageSize),
		placeholderData: (previousData) => previousData,
	});

	// Retry mutation
	const retryMutation = useMutation({
		mutationFn: api.retryTask,
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: ["tasks"] });
		},
	});

	// Delete mutation
	const deleteMutation = useMutation({
		mutationFn: api.deleteTask,
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: ["tasks"] });
		},
	});

	// Table columns
	const columns = useMemo(
		() => [
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
				cell: (info) => <span className="text-zinc-600 dark:text-zinc-400">{info.getValue()}</span>,
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
						{formatDistanceToNow(new Date(info.getValue()), {
							addSuffix: true,
						})}
					</span>
				),
			}),
			columnHelper.accessor("duration_ms", {
				header: "Duration",
				cell: (info) => {
					const value = info.getValue();
					if (value === null) return <span className="text-zinc-400">—</span>;
					return (
						<span className="text-zinc-600 dark:text-zinc-400">
							{value < 1000 ? `${value}ms` : `${(value / 1000).toFixed(2)}s`}
						</span>
					);
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
					const canRetry = task.status === "failed" || task.status === "cancelled";
					const canDelete = task.status !== "running";

					return (
						<div className="flex items-center justify-end gap-1">
							{canRetry && (
								<Button
									variant="ghost"
									size="icon-sm"
									onPress={() => retryMutation.mutate(task.id)}
									isDisabled={retryMutation.isPending}
									aria-label="Retry task"
								>
									<RefreshCw className="h-4 w-4" />
								</Button>
							)}
							{canDelete && (
								<Button
									variant="ghost"
									size="icon-sm"
									onPress={() => deleteMutation.mutate(task.id)}
									isDisabled={deleteMutation.isPending}
									aria-label="Delete task"
								>
									<Trash2 className="h-4 w-4" />
								</Button>
							)}
						</div>
					);
				},
			}),
		],
		[retryMutation, deleteMutation],
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

	return (
		<div className="space-y-4">
			{/* Filters */}
			<Card padding="sm">
				<CardContent className="flex flex-wrap items-center gap-4 p-4">
					{/* Search */}
					<div className="relative flex-1 min-w-[200px]">
						<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
						<input
							type="search"
							placeholder="Search tasks by name or ID..."
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							className="h-10 w-full rounded-lg border border-zinc-300 bg-white pl-10 pr-3 text-sm outline-none placeholder:text-zinc-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
						/>
					</div>

					{/* Status filter */}
					<Select<{ value: string; label: string }>
						selectedKey={statusFilter}
						onSelectionChange={(key) => setStatusFilter(key as TaskStatus | "all")}
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
					<input
						type="text"
						placeholder="Queue name..."
						value={queueFilter}
						onChange={(e) => setQueueFilter(e.target.value)}
						className="h-10 w-40 rounded-lg border border-zinc-300 bg-white px-3 text-sm outline-none placeholder:text-zinc-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
					/>

					{/* Refresh button */}
					<Button variant="secondary" size="md" onPress={() => refetch()} isDisabled={isLoading}>
						<RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
						Refresh
					</Button>
				</CardContent>
			</Card>

			{/* Tasks table */}
			<Card padding="none">
				{isLoading && !data ? (
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
												No tasks found
											</td>
										</tr>
									) : (
										table.getRowModel().rows.map((row) => (
											<tr key={row.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50">
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
									{page * pageSize + 1}-{Math.min((page + 1) * pageSize, data?.total ?? 0)}
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
									Page {page + 1} of {totalPages}
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
		</div>
	);
}

/**
 * Application router configuration.
 * Uses React Router v6 with lazy loading for code splitting.
 */

import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { RootLayout } from "@/components/layout/RootLayout";
import { LoadingOverlay } from "@/components/ui";

// Lazy load page components for code splitting
const DashboardPage = lazy(() => import("@/pages/Dashboard"));
const TasksPage = lazy(() => import("@/pages/Tasks"));
const WorkersPage = lazy(() => import("@/pages/Workers"));
const QueuesPage = lazy(() => import("@/pages/Queues"));
const SettingsPage = lazy(() => import("@/pages/Settings"));

/**
 * Page wrapper with Suspense for lazy loading.
 */
function PageLoader({ children }: { children: React.ReactNode }): React.ReactNode {
	return <Suspense fallback={<LoadingOverlay label="Loading page..." />}>{children}</Suspense>;
}

/**
 * Simple 404 page component.
 */
function NotFound(): React.ReactNode {
	return (
		<div className="flex flex-col items-center justify-center py-12 text-center">
			<h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">404</h1>
			<p className="text-gray-500 dark:text-gray-400 mb-6">Page not found</p>
			<a
				href="/"
				className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
			>
				Go back home
			</a>
		</div>
	);
}

/**
 * Router configuration.
 */
export const router = createBrowserRouter([
	{
		path: "/",
		element: <RootLayout />,
		children: [
			{
				index: true,
				element: (
					<PageLoader>
						<DashboardPage />
					</PageLoader>
				),
			},
			{
				path: "tasks",
				element: (
					<PageLoader>
						<TasksPage />
					</PageLoader>
				),
			},
			{
				path: "workers",
				element: (
					<PageLoader>
						<WorkersPage />
					</PageLoader>
				),
			},
			{
				path: "queues",
				element: (
					<PageLoader>
						<QueuesPage />
					</PageLoader>
				),
			},
			{
				path: "settings",
				element: (
					<PageLoader>
						<SettingsPage />
					</PageLoader>
				),
			},
			{
				path: "*",
				element: <NotFound />,
			},
		],
	},
]);

/**
 * Router component that provides navigation context.
 */
export function Router(): React.ReactNode {
	return <RouterProvider router={router} />;
}

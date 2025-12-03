/**
 * React Query configuration and provider setup.
 * Follows TanStack Query v5 best practices.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { type ReactNode, useState } from "react";

/**
 * Create a QueryClient with optimized defaults for real-time monitoring.
 */
function makeQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: {
				// Keep data fresh for 5 seconds before considering it stale
				staleTime: 5 * 1000,
				// Cache data for 5 minutes
				gcTime: 5 * 60 * 1000,
				// Don't refetch on window focus for real-time data
				refetchOnWindowFocus: false,
				// Only retry once on failure
				retry: 1,
				// Retry after 1 second
				retryDelay: 1000,
				// Use structural sharing for efficient updates
				structuralSharing: true,
			},
			mutations: {
				// Retry mutations once
				retry: 1,
				// Retry after 1 second
				retryDelay: 1000,
			},
		},
	});
}

interface QueryProviderProps {
	children: ReactNode;
}

/**
 * Query provider component that creates a stable QueryClient instance.
 * Uses useState to ensure the client persists across re-renders but
 * is unique per component instance (important for SSR).
 */
export function QueryProvider({ children }: QueryProviderProps): ReactNode {
	// Create QueryClient in state to ensure it persists across renders
	// This pattern is recommended by TanStack Query for client-side apps
	const [queryClient] = useState(() => makeQueryClient());

	return (
		<QueryClientProvider client={queryClient}>
			{children}
			{/* DevTools only render in development */}
			<ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-right" />
		</QueryClientProvider>
	);
}

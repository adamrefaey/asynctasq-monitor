/**
 * Test utilities for React Testing Library.
 * Provides wrapper components and helper functions for testing.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type RenderOptions, render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

/**
 * Create a fresh QueryClient for each test.
 * Disables retries and caching for predictable test behavior.
 */
export function createTestQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: {
				retry: false,
				gcTime: 0,
				staleTime: 0,
			},
			mutations: {
				retry: false,
			},
		},
	});
}

interface AllProvidersProps {
	children: ReactNode;
	queryClient?: QueryClient | undefined;
}

/**
 * Wrapper component that provides all necessary context providers.
 */
function AllProviders({ children, queryClient }: AllProvidersProps): ReactNode {
	const client = queryClient ?? createTestQueryClient();

	return (
		<QueryClientProvider client={client}>
			<MemoryRouter
				future={{
					v7_startTransition: true,
					v7_relativeSplatPath: true,
				}}
			>
				{children}
			</MemoryRouter>
		</QueryClientProvider>
	);
}

interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
	queryClient?: QueryClient;
}

/**
 * Custom render function that wraps components with all providers.
 * Returns the render result plus a user-event instance for interactions.
 */
export function renderWithProviders(
	ui: ReactElement,
	options?: CustomRenderOptions,
): ReturnType<typeof render> & { user: ReturnType<typeof userEvent.setup> } {
	const { queryClient, ...renderOptions } = options ?? {};

	const wrapper = ({ children }: { children: ReactNode }) => (
		<AllProviders queryClient={queryClient}>{children}</AllProviders>
	);

	const user = userEvent.setup();

	return {
		user,
		...render(ui, { wrapper, ...renderOptions }),
	};
}

// Re-export everything from React Testing Library
export * from "@testing-library/react";
export { userEvent };

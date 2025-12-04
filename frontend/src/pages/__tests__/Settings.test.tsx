/**
 * Tests for the Settings page component.
 *
 * Tests cover:
 * - Page rendering
 * - Section navigation
 * - Theme toggle
 * - Settings form elements
 * - Reset functionality
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import Settings from "../Settings";

// Mock the settings store
vi.mock("@/hooks/useSettings", () => ({
	useSettingsStore: Object.assign(
		vi.fn(() => ({
			theme: "system",
			timezone: "UTC",
			dateFormat: "relative",
			refreshInterval: 5,
			tableDensity: "comfortable",
			itemsPerPage: 50,
			apiUrl: "/api",
			wsUrl: "ws://localhost:8000/ws",
			timeout: 30,
			enableNotifications: true,
			notifyOnFailure: true,
			notifyOnComplete: false,
			soundEnabled: false,
			debugMode: false,
			cacheEnabled: true,
			maxRetries: 3,
			logLevel: "info",
			setTheme: vi.fn(),
			setTimezone: vi.fn(),
			setDateFormat: vi.fn(),
			setRefreshInterval: vi.fn(),
			setTableDensity: vi.fn(),
			setItemsPerPage: vi.fn(),
			setApiUrl: vi.fn(),
			setWsUrl: vi.fn(),
			setTimeout: vi.fn(),
			setEnableNotifications: vi.fn(),
			setNotifyOnFailure: vi.fn(),
			setNotifyOnComplete: vi.fn(),
			setSoundEnabled: vi.fn(),
			setDebugMode: vi.fn(),
			setCacheEnabled: vi.fn(),
			setMaxRetries: vi.fn(),
			setLogLevel: vi.fn(),
			resetToDefaults: vi.fn(),
			clearAllData: vi.fn(),
		})),
		{
			getState: vi.fn(() => ({
				setTheme: vi.fn(),
			})),
		},
	),
}));

// Mock the theme hook
vi.mock("@/hooks/useTheme", () => ({
	useTheme: vi.fn(() => ({
		theme: "light",
		setTheme: vi.fn(),
	})),
}));

describe("Settings", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("renders settings page header", async () => {
		renderWithProviders(<Settings />);

		expect(screen.getByText("Settings")).toBeInTheDocument();
		expect(screen.getByText("Configure your monitoring dashboard preferences")).toBeInTheDocument();
	});

	it("renders reset to defaults button", async () => {
		renderWithProviders(<Settings />);

		expect(screen.getByText("Reset to Defaults")).toBeInTheDocument();
	});

	it("renders navigation sections", async () => {
		renderWithProviders(<Settings />);

		expect(screen.getByText("General")).toBeInTheDocument();
		expect(screen.getByText("Connection")).toBeInTheDocument();
		expect(screen.getByText("Notifications")).toBeInTheDocument();
		expect(screen.getByText("Advanced")).toBeInTheDocument();
	});

	it("renders general settings section by default", async () => {
		renderWithProviders(<Settings />);

		// Check general settings content
		expect(screen.getByText("General Settings")).toBeInTheDocument();
		expect(screen.getByText("Theme")).toBeInTheDocument();
		expect(screen.getByText("Auto Refresh Interval")).toBeInTheDocument();
		expect(screen.getByText("Timezone")).toBeInTheDocument();
	});

	it("renders theme toggle buttons", async () => {
		renderWithProviders(<Settings />);

		// Check theme buttons
		expect(screen.getByText("Light")).toBeInTheDocument();
		expect(screen.getByText("Dark")).toBeInTheDocument();
		expect(screen.getByText("System")).toBeInTheDocument();
	});

	it("renders date format options", async () => {
		renderWithProviders(<Settings />);

		expect(screen.getByText("Date Format")).toBeInTheDocument();
		expect(screen.getByText("Relative")).toBeInTheDocument();
		expect(screen.getByText("Absolute")).toBeInTheDocument();
	});

	it("renders table density options", async () => {
		renderWithProviders(<Settings />);

		expect(screen.getByText("Table Density")).toBeInTheDocument();
		expect(screen.getByText("Compact")).toBeInTheDocument();
		expect(screen.getByText("Comfortable")).toBeInTheDocument();
		expect(screen.getByText("Spacious")).toBeInTheDocument();
	});

	it("renders items per page options", async () => {
		renderWithProviders(<Settings />);

		expect(screen.getByText("Items Per Page")).toBeInTheDocument();
		expect(screen.getByText("25")).toBeInTheDocument();
		expect(screen.getByText("50")).toBeInTheDocument();
		expect(screen.getByText("100")).toBeInTheDocument();
	});

	it("can navigate to connection settings", async () => {
		const { user } = renderWithProviders(<Settings />);

		// Click on Connection nav button
		await user.click(screen.getByText("Connection"));

		await waitFor(() => {
			expect(screen.getByText("Connection Settings")).toBeInTheDocument();
		});

		// Check connection settings content
		expect(screen.getByText("API URL")).toBeInTheDocument();
		expect(screen.getByText("WebSocket URL")).toBeInTheDocument();
		expect(screen.getByText("Request Timeout")).toBeInTheDocument();
	});

	it("can navigate to notifications settings", async () => {
		const { user } = renderWithProviders(<Settings />);

		// Click on Notifications nav button
		await user.click(screen.getByText("Notifications"));

		await waitFor(() => {
			expect(screen.getByText("Notification Settings")).toBeInTheDocument();
		});
	});

	it("can navigate to advanced settings", async () => {
		const { user } = renderWithProviders(<Settings />);

		// Click on Advanced nav button
		await user.click(screen.getByText("Advanced"));

		await waitFor(() => {
			expect(screen.getByText("Advanced Settings")).toBeInTheDocument();
		});

		// Check advanced settings content
		expect(screen.getByText("Debug Mode")).toBeInTheDocument();
		expect(screen.getByText("Cache Enabled")).toBeInTheDocument();
	});

	it("displays timezone selector", async () => {
		renderWithProviders(<Settings />);

		// Check timezone options exist in select
		expect(screen.getByText("UTC")).toBeInTheDocument();
	});

	it("displays connection status badges", async () => {
		const { user } = renderWithProviders(<Settings />);

		// Navigate to connection settings
		await user.click(screen.getByText("Connection"));

		await waitFor(() => {
			expect(screen.getByText("Connection Status")).toBeInTheDocument();
		});

		// Check status badges
		const connectedBadges = screen.getAllByText("Connected");
		expect(connectedBadges.length).toBe(2);
	});
});

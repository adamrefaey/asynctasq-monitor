/**
 * Settings page component.
 * Allows users to configure dashboard preferences with persistence.
 */

import {
	Bell,
	Clock,
	Globe,
	Moon,
	Palette,
	RefreshCw,
	Server,
	Shield,
	Sun,
	Trash2,
	Zap,
} from "lucide-react";
import { useState } from "react";
import { Badge, Button, Card, TextField } from "@/components/ui";
import { type LogLevel, type TimezoneOption, useSettingsStore } from "@/hooks/useSettings";
import { useTheme } from "@/hooks/useTheme";

type SettingsSection = "general" | "connection" | "notifications" | "advanced";

interface SettingRowProps {
	icon: typeof Sun;
	title: string;
	description: string;
	children: React.ReactNode;
}

function SettingRow({ icon: Icon, title, description, children }: SettingRowProps) {
	return (
		<div className="flex flex-col gap-4 py-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-100 dark:border-gray-700 last:border-0">
			<div className="flex items-start gap-3">
				<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
					<Icon className="h-5 w-5" />
				</div>
				<div>
					<h4 className="font-medium text-gray-900 dark:text-white">{title}</h4>
					<p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
				</div>
			</div>
			<div className="ml-13 sm:ml-0">{children}</div>
		</div>
	);
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
	return (
		<button
			type="button"
			role="switch"
			aria-checked={checked}
			onClick={() => onChange(!checked)}
			className={`
        relative inline-flex h-6 w-11 items-center rounded-full transition-colors
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        dark:focus:ring-offset-gray-900
        ${checked ? "bg-blue-600" : "bg-gray-200 dark:bg-gray-700"}
      `}
		>
			<span
				className={`
          inline-block h-4 w-4 transform rounded-full bg-white transition-transform
          ${checked ? "translate-x-6" : "translate-x-1"}
        `}
			/>
		</button>
	);
}

function NavButton({
	active,
	icon: Icon,
	label,
	onClick,
}: {
	active: boolean;
	icon: typeof Sun;
	label: string;
	onClick: () => void;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			className={`
        flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors
        ${
					active
						? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
						: "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
				}
      `}
		>
			<Icon className="h-4 w-4" />
			{label}
		</button>
	);
}

export default function Settings() {
	const { theme: resolvedTheme, setTheme } = useTheme();
	const [section, setSection] = useState<SettingsSection>("general");

	// Use Zustand store for all settings
	const {
		theme,
		timezone,
		dateFormat,
		refreshInterval,
		tableDensity,
		itemsPerPage,
		apiUrl,
		wsUrl,
		timeout,
		enableNotifications,
		notifyOnFailure,
		notifyOnComplete,
		soundEnabled,
		debugMode,
		cacheEnabled,
		maxRetries,
		logLevel,
		setTimezone,
		setDateFormat,
		setRefreshInterval,
		setTableDensity,
		setItemsPerPage,
		setApiUrl,
		setWsUrl,
		setTimeout: setTimeoutSetting,
		setEnableNotifications,
		setNotifyOnFailure,
		setNotifyOnComplete,
		setSoundEnabled,
		setDebugMode,
		setCacheEnabled,
		setMaxRetries,
		setLogLevel,
		resetToDefaults,
		clearAllData,
	} = useSettingsStore();

	// Track theme setting separately to update both store and useTheme hook
	const handleThemeChange = (newTheme: "light" | "dark" | "system") => {
		useSettingsStore.getState().setTheme(newTheme);
		setTheme(newTheme);
	};

	const handleReset = () => {
		resetToDefaults();
		// Also reset the theme hook
		setTheme("system");
	};

	const handleClearData = () => {
		if (window.confirm("Are you sure you want to clear all data? This action cannot be undone.")) {
			clearAllData();
			setTheme("system");
		}
	};

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
					<p className="text-gray-500 dark:text-gray-400">
						Configure your monitoring dashboard preferences
					</p>
				</div>
				<div className="flex gap-2">
					<Button variant="outline" onPress={handleReset}>
						<RefreshCw className="h-4 w-4" />
						Reset to Defaults
					</Button>
				</div>
			</div>

			<div className="flex flex-col gap-6 lg:flex-row">
				{/* Navigation */}
				<nav className="flex flex-row gap-2 lg:flex-col lg:w-48">
					<NavButton
						active={section === "general"}
						icon={Palette}
						label="General"
						onClick={() => setSection("general")}
					/>
					<NavButton
						active={section === "connection"}
						icon={Server}
						label="Connection"
						onClick={() => setSection("connection")}
					/>
					<NavButton
						active={section === "notifications"}
						icon={Bell}
						label="Notifications"
						onClick={() => setSection("notifications")}
					/>
					<NavButton
						active={section === "advanced"}
						icon={Zap}
						label="Advanced"
						onClick={() => setSection("advanced")}
					/>
				</nav>

				{/* Content */}
				<div className="flex-1">
					{section === "general" && (
						<Card>
							<Card.Header>
								<h3 className="text-lg font-semibold text-gray-900 dark:text-white">
									General Settings
								</h3>
							</Card.Header>
							<Card.Content>
								<SettingRow
									icon={resolvedTheme === "dark" ? Moon : Sun}
									title="Theme"
									description="Choose your preferred color scheme"
								>
									<div className="flex gap-2">
										{(["light", "dark", "system"] as const).map((t) => (
											<Button
												key={t}
												variant={theme === t ? "primary" : "outline"}
												size="sm"
												onPress={() => handleThemeChange(t)}
											>
												{t === "light" && <Sun className="h-4 w-4" />}
												{t === "dark" && <Moon className="h-4 w-4" />}
												{t === "system" && <Palette className="h-4 w-4" />}
												{t.charAt(0).toUpperCase() + t.slice(1)}
											</Button>
										))}
									</div>
								</SettingRow>

								<SettingRow
									icon={RefreshCw}
									title="Auto Refresh Interval"
									description="How often to refresh data automatically"
								>
									<div className="flex items-center gap-2">
										<TextField
											aria-label="Auto refresh interval in seconds"
											type="number"
											value={String(refreshInterval)}
											onChange={(v) => setRefreshInterval(Number(v) || 5)}
											className="w-20"
										/>
										<span className="text-sm text-gray-500">seconds</span>
									</div>
								</SettingRow>

								<SettingRow
									icon={Globe}
									title="Timezone"
									description="Timezone for displaying dates and times"
								>
									<select
										aria-label="Select timezone"
										value={timezone}
										onChange={(e) => setTimezone(e.target.value as TimezoneOption)}
										className="
                      rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm
                      dark:border-gray-600 dark:bg-gray-800 dark:text-white
                      focus:outline-none focus:ring-2 focus:ring-blue-500
                    "
									>
										<option value="UTC">UTC</option>
										<option value="auto">Auto-detect</option>
										<option value="America/New_York">Eastern Time</option>
										<option value="America/Los_Angeles">Pacific Time</option>
										<option value="Europe/London">London</option>
										<option value="Asia/Tokyo">Tokyo</option>
									</select>
								</SettingRow>

								<SettingRow
									icon={Clock}
									title="Date Format"
									description="How to display dates and times"
								>
									<div className="flex gap-2">
										{(["relative", "absolute"] as const).map((format) => (
											<Button
												key={format}
												variant={dateFormat === format ? "primary" : "outline"}
												size="sm"
												onPress={() => setDateFormat(format)}
											>
												{format.charAt(0).toUpperCase() + format.slice(1)}
											</Button>
										))}
									</div>
								</SettingRow>

								<SettingRow
									icon={Palette}
									title="Table Density"
									description="Adjust the spacing of table rows"
								>
									<div className="flex gap-2">
										{(["compact", "comfortable", "spacious"] as const).map((density) => (
											<Button
												key={density}
												variant={tableDensity === density ? "primary" : "outline"}
												size="sm"
												onPress={() => setTableDensity(density)}
											>
												{density.charAt(0).toUpperCase() + density.slice(1)}
											</Button>
										))}
									</div>
								</SettingRow>

								<SettingRow
									icon={Zap}
									title="Items Per Page"
									description="Default number of items per page in tables"
								>
									<div className="flex gap-2">
										{([25, 50, 100] as const).map((count) => (
											<Button
												key={count}
												variant={itemsPerPage === count ? "primary" : "outline"}
												size="sm"
												onPress={() => setItemsPerPage(count)}
											>
												{count}
											</Button>
										))}
									</div>
								</SettingRow>
							</Card.Content>
						</Card>
					)}

					{section === "connection" && (
						<Card>
							<Card.Header>
								<h3 className="text-lg font-semibold text-gray-900 dark:text-white">
									Connection Settings
								</h3>
							</Card.Header>
							<Card.Content>
								<SettingRow icon={Server} title="API URL" description="Backend API endpoint URL">
									<TextField
										aria-label="API URL"
										value={apiUrl}
										onChange={(v) => setApiUrl(v)}
										className="w-64"
									/>
								</SettingRow>

								<SettingRow
									icon={Zap}
									title="WebSocket URL"
									description="Real-time updates WebSocket endpoint"
								>
									<TextField
										aria-label="WebSocket URL"
										value={wsUrl}
										onChange={(v) => setWsUrl(v)}
										className="w-64"
									/>
								</SettingRow>

								<SettingRow
									icon={Clock}
									title="Request Timeout"
									description="Maximum time to wait for API responses"
								>
									<div className="flex items-center gap-2">
										<TextField
											aria-label="Request timeout in seconds"
											type="number"
											value={String(timeout)}
											onChange={(v) => setTimeoutSetting(Number(v) || 30)}
											className="w-20"
										/>
										<span className="text-sm text-gray-500">seconds</span>
									</div>
								</SettingRow>

								<div className="mt-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 p-4">
									<div className="flex items-start gap-3">
										<Shield className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
										<div>
											<h4 className="font-medium text-blue-800 dark:text-blue-300">
												Connection Status
											</h4>
											<p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
												API:{" "}
												<Badge variant="success" size="sm">
													Connected
												</Badge>{" "}
												WebSocket:{" "}
												<Badge variant="success" size="sm">
													Connected
												</Badge>
											</p>
										</div>
									</div>
								</div>
							</Card.Content>
						</Card>
					)}

					{section === "notifications" && (
						<Card>
							<Card.Header>
								<h3 className="text-lg font-semibold text-gray-900 dark:text-white">
									Notification Settings
								</h3>
							</Card.Header>
							<Card.Content>
								<SettingRow
									icon={Bell}
									title="Enable Notifications"
									description="Show browser notifications for events"
								>
									<Toggle
										checked={enableNotifications}
										onChange={(v) => setEnableNotifications(v)}
									/>
								</SettingRow>

								<SettingRow
									icon={Bell}
									title="Notify on Task Failure"
									description="Get notified when a task fails"
								>
									<Toggle checked={notifyOnFailure} onChange={(v) => setNotifyOnFailure(v)} />
								</SettingRow>

								<SettingRow
									icon={Bell}
									title="Notify on Task Complete"
									description="Get notified when a task completes successfully"
								>
									<Toggle checked={notifyOnComplete} onChange={(v) => setNotifyOnComplete(v)} />
								</SettingRow>

								<SettingRow
									icon={Bell}
									title="Sound Alerts"
									description="Play sound when notifications appear"
								>
									<Toggle checked={soundEnabled} onChange={(v) => setSoundEnabled(v)} />
								</SettingRow>
							</Card.Content>
						</Card>
					)}

					{section === "advanced" && (
						<Card>
							<Card.Header>
								<h3 className="text-lg font-semibold text-gray-900 dark:text-white">
									Advanced Settings
								</h3>
							</Card.Header>
							<Card.Content>
								<SettingRow
									icon={Zap}
									title="Debug Mode"
									description="Enable verbose logging and debug features"
								>
									<Toggle checked={debugMode} onChange={(v) => setDebugMode(v)} />
								</SettingRow>

								<SettingRow
									icon={Server}
									title="Cache Enabled"
									description="Cache API responses for better performance"
								>
									<Toggle checked={cacheEnabled} onChange={(v) => setCacheEnabled(v)} />
								</SettingRow>

								<SettingRow
									icon={RefreshCw}
									title="Max Retries"
									description="Maximum retry attempts for failed requests"
								>
									<TextField
										aria-label="Maximum retry attempts"
										type="number"
										value={String(maxRetries)}
										onChange={(v) => setMaxRetries(Number(v) || 3)}
										className="w-20"
									/>
								</SettingRow>

								<SettingRow
									icon={Shield}
									title="Log Level"
									description="Minimum log level to record"
								>
									<select
										aria-label="Select log level"
										value={logLevel}
										onChange={(e) => setLogLevel(e.target.value as LogLevel)}
										className="
                      rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm
                      dark:border-gray-600 dark:bg-gray-800 dark:text-white
                      focus:outline-none focus:ring-2 focus:ring-blue-500
                    "
									>
										<option value="debug">Debug</option>
										<option value="info">Info</option>
										<option value="warn">Warning</option>
										<option value="error">Error</option>
									</select>
								</SettingRow>

								<div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-700">
									<h4 className="font-medium text-red-600 dark:text-red-400 mb-2">Danger Zone</h4>
									<div className="flex flex-col gap-3 sm:flex-row">
										<Button variant="outline" onPress={handleReset}>
											<RefreshCw className="h-4 w-4" />
											Reset All Settings
										</Button>
										<Button variant="danger" onPress={handleClearData}>
											<Trash2 className="h-4 w-4" />
											Clear All Data
										</Button>
									</div>
								</div>
							</Card.Content>
						</Card>
					)}
				</div>
			</div>

			{/* Keyboard shortcuts hint */}
			<div className="mt-8 text-center">
				<p className="text-sm text-gray-500 dark:text-gray-400">
					Press{" "}
					<kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded border border-gray-300 bg-gray-100 px-1 font-mono text-xs dark:border-gray-600 dark:bg-gray-800">
						?
					</kbd>{" "}
					to view keyboard shortcuts
				</p>
			</div>
		</div>
	);
}

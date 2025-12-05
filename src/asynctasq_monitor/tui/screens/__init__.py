"""TUI screens for asynctasq-monitor.

This package contains all screen definitions for the TUI.
"""

from asynctasq_monitor.tui.screens.dashboard import DashboardScreen
from asynctasq_monitor.tui.screens.help import HelpScreen
from asynctasq_monitor.tui.screens.task_detail import TaskDetailScreen
from asynctasq_monitor.tui.screens.tasks import TasksScreen

__all__ = ["DashboardScreen", "HelpScreen", "TaskDetailScreen", "TasksScreen"]

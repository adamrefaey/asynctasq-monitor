"""Unit tests for the TaskDetailScreen."""

from datetime import UTC, datetime

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label, Static

from asynctasq_monitor.models.task import Task, TaskStatus
from asynctasq_monitor.tui.screens.task_detail import TaskDetailScreen


class TestTaskDetailScreen:
    """Tests for the TaskDetailScreen modal."""

    @pytest.fixture
    def sample_task(self) -> Task:
        """Create a sample task for testing."""
        now = datetime.now(UTC)
        return Task(
            id="test-task-1234-5678-9abc-def0",
            name="test_task",
            queue="default",
            status=TaskStatus.COMPLETED,
            enqueued_at=now,
            started_at=now,
            completed_at=now,
            duration_ms=1234,
            worker_id="worker-123",
            attempt=1,
            max_retries=3,
            args=["arg1", "arg2"],
            kwargs={"key": "value"},
            result={"success": True},
        )

    @pytest.fixture
    def failed_task(self) -> Task:
        """Create a failed task for testing."""
        now = datetime.now(UTC)
        return Task(
            id="failed-task-1234-5678-9abc",
            name="failed_task",
            queue="high",
            status=TaskStatus.FAILED,
            enqueued_at=now,
            started_at=now,
            completed_at=now,
            duration_ms=5000,
            exception="TestError: Something went wrong",
            traceback="Traceback (most recent call last):\n  File ...\nTestError",
        )

    @pytest.fixture
    def pending_task(self) -> Task:
        """Create a pending task for testing."""
        now = datetime.now(UTC)
        return Task(
            id="pending-task-1234-5678-9abc",
            name="pending_task",
            queue="low",
            status=TaskStatus.PENDING,
            enqueued_at=now,
        )

    def test_init_stores_task(self, sample_task: Task) -> None:
        """Test that init stores the task."""
        screen = TaskDetailScreen(sample_task)
        assert screen.task_data == sample_task

    @pytest.mark.asyncio
    async def test_compose_yields_container(self, sample_task: Task) -> None:
        """Test that compose yields the expected container structure."""
        from textual.containers import Container

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test() as pilot:
            # Push the modal screen
            app.push_screen(TaskDetailScreen(sample_task))
            await pilot.pause()

            # Check main container exists
            container = app.screen.query_one("#task-detail-container", Container)
            assert container is not None

    @pytest.mark.asyncio
    async def test_header_shows_task_id(self, sample_task: Task) -> None:
        """Test that header shows truncated task ID."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(TaskDetailScreen(sample_task))
            await pilot.pause()

            header = app.screen.query_one("#task-detail-header Label", Label)
            assert sample_task.id[:16] in str(header.render())

    @pytest.mark.asyncio
    async def test_completed_task_has_close_button(self, sample_task: Task) -> None:
        """Test that completed task has close button."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(TaskDetailScreen(sample_task))
            await pilot.pause()

            close_btn = app.screen.query_one("#close-btn", Button)
            assert close_btn is not None

    @pytest.mark.asyncio
    async def test_failed_task_has_retry_button(self, failed_task: Task) -> None:
        """Test that failed task has retry button."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(TaskDetailScreen(failed_task))
            await pilot.pause()

            retry_btn = app.screen.query_one("#retry-btn", Button)
            assert retry_btn is not None

    @pytest.mark.asyncio
    async def test_pending_task_has_cancel_button(self, pending_task: Task) -> None:
        """Test that pending task has cancel button."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(TaskDetailScreen(pending_task))
            await pilot.pause()

            cancel_btn = app.screen.query_one("#cancel-btn", Button)
            assert cancel_btn is not None

    @pytest.mark.asyncio
    async def test_completed_task_no_retry_or_cancel(self, sample_task: Task) -> None:
        """Test that completed task has no retry or cancel buttons."""
        from textual.css.query import NoMatches

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(TaskDetailScreen(sample_task))
            await pilot.pause()

            # Retry and cancel should not exist for completed task
            with pytest.raises(NoMatches):
                app.screen.query_one("#retry-btn", Button)

            with pytest.raises(NoMatches):
                app.screen.query_one("#cancel-btn", Button)

    @pytest.mark.asyncio
    async def test_failed_task_shows_exception(self, failed_task: Task) -> None:
        """Test that failed task shows exception content."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(TaskDetailScreen(failed_task))
            await pilot.pause()

            exception_content = app.screen.query_one("#exception-content", Static)
            assert exception_content is not None

    @pytest.mark.asyncio
    async def test_task_with_result_shows_result(self, sample_task: Task) -> None:
        """Test that task with result shows result content."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(TaskDetailScreen(sample_task))
            await pilot.pause()

            result_content = app.screen.query_one("#result-content", Static)
            assert result_content is not None

    @pytest.mark.asyncio
    async def test_task_with_args_shows_args(self, sample_task: Task) -> None:
        """Test that task with args shows args content."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(TaskDetailScreen(sample_task))
            await pilot.pause()

            args_content = app.screen.query_one("#args-content", Static)
            assert args_content is not None

    @pytest.mark.asyncio
    async def test_close_button_dismisses(self, sample_task: Task) -> None:
        """Test that close button dismisses the modal."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(TaskDetailScreen(sample_task))
            await pilot.pause()

            # Verify we're on the modal
            assert isinstance(app.screen, TaskDetailScreen)

            # Click close button - use button press simulation instead of pilot.click
            close_btn = app.screen.query_one("#close-btn", Button)
            close_btn.press()
            await pilot.pause()

            # Modal should be dismissed
            assert not isinstance(app.screen, TaskDetailScreen)

    @pytest.mark.asyncio
    async def test_escape_dismisses(self, sample_task: Task) -> None:
        """Test that escape key dismisses the modal."""

        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield from ()

        app = TestApp()
        async with app.run_test() as pilot:
            app.push_screen(TaskDetailScreen(sample_task))
            await pilot.pause()

            # Verify we're on the modal
            assert isinstance(app.screen, TaskDetailScreen)

            # Press escape
            await pilot.press("escape")
            await pilot.pause()

            # Modal should be dismissed
            assert not isinstance(app.screen, TaskDetailScreen)

    def test_can_retry_for_failed_task(self, failed_task: Task) -> None:
        """Test _can_retry returns True for failed task."""
        screen = TaskDetailScreen(failed_task)
        assert screen._can_retry() is True

    def test_can_retry_for_cancelled_task(self) -> None:
        """Test _can_retry returns True for cancelled task."""
        now = datetime.now(UTC)
        task = Task(
            id="cancelled-task",
            name="cancelled",
            queue="default",
            status=TaskStatus.CANCELLED,
            enqueued_at=now,
        )
        screen = TaskDetailScreen(task)
        assert screen._can_retry() is True

    def test_can_retry_for_completed_task(self, sample_task: Task) -> None:
        """Test _can_retry returns False for completed task."""
        screen = TaskDetailScreen(sample_task)
        assert screen._can_retry() is False

    def test_can_cancel_for_pending_task(self, pending_task: Task) -> None:
        """Test _can_cancel returns True for pending task."""
        screen = TaskDetailScreen(pending_task)
        assert screen._can_cancel() is True

    def test_can_cancel_for_running_task(self) -> None:
        """Test _can_cancel returns True for running task."""
        now = datetime.now(UTC)
        task = Task(
            id="running-task",
            name="running",
            queue="default",
            status=TaskStatus.RUNNING,
            enqueued_at=now,
        )
        screen = TaskDetailScreen(task)
        assert screen._can_cancel() is True

    def test_can_cancel_for_completed_task(self, sample_task: Task) -> None:
        """Test _can_cancel returns False for completed task."""
        screen = TaskDetailScreen(sample_task)
        assert screen._can_cancel() is False

    def test_format_datetime_with_none(self, sample_task: Task) -> None:
        """Test _format_datetime returns dash for None."""
        screen = TaskDetailScreen(sample_task)
        assert screen._format_datetime(None) == "-"

    def test_format_datetime_with_datetime(self, sample_task: Task) -> None:
        """Test _format_datetime formats datetime correctly."""
        screen = TaskDetailScreen(sample_task)
        dt = datetime(2025, 1, 15, 10, 30, 45, tzinfo=UTC)
        formatted = screen._format_datetime(dt)
        assert "2025-01-15" in formatted
        assert "10:30:45" in formatted

    def test_format_args_with_args_only(self) -> None:
        """Test _format_args with only args."""
        now = datetime.now(UTC)
        task = Task(
            id="task-id",
            name="task",
            queue="default",
            status=TaskStatus.PENDING,
            enqueued_at=now,
            args=["arg1", "arg2"],
        )
        screen = TaskDetailScreen(task)
        formatted = screen._format_args()
        assert "args:" in formatted
        assert "arg1" in formatted

    def test_format_args_with_kwargs_only(self) -> None:
        """Test _format_args with only kwargs."""
        now = datetime.now(UTC)
        task = Task(
            id="task-id",
            name="task",
            queue="default",
            status=TaskStatus.PENDING,
            enqueued_at=now,
            kwargs={"key": "value"},
        )
        screen = TaskDetailScreen(task)
        formatted = screen._format_args()
        assert "kwargs:" in formatted
        assert "key" in formatted

    def test_format_args_with_both(self, sample_task: Task) -> None:
        """Test _format_args with both args and kwargs."""
        screen = TaskDetailScreen(sample_task)
        formatted = screen._format_args()
        assert "args:" in formatted
        assert "kwargs:" in formatted

    def test_format_args_with_neither(self, pending_task: Task) -> None:
        """Test _format_args with no args or kwargs."""
        screen = TaskDetailScreen(pending_task)
        formatted = screen._format_args()
        assert formatted == "-"

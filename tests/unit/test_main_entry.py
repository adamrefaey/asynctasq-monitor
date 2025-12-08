"""Tests for __main__.py entry point.

Tests for the CLI entry point module that handles KeyboardInterrupt
and proper exit codes.
"""

from unittest.mock import patch

import pytest


class TestMainEntry:
    """Tests for the __main__ module entry point."""

    @pytest.mark.unit
    def test_main_successful_exit(self) -> None:
        """Test that main() returns 0 on successful execution."""
        from asynctasq_monitor.__main__ import main

        with patch("asynctasq_monitor.cli.main.app") as mock_app:
            result = main()
            assert result == 0
            mock_app.assert_called_once()

    @pytest.mark.unit
    def test_main_keyboard_interrupt(self) -> None:
        """Test that main() returns 130 on KeyboardInterrupt."""
        from asynctasq_monitor.__main__ import main

        with patch("asynctasq_monitor.cli.main.app", side_effect=KeyboardInterrupt):
            result = main()
            assert result == 130

    @pytest.mark.unit
    def test_main_general_exception_propagates(self) -> None:
        """Test that general exceptions are not caught."""
        from asynctasq_monitor.__main__ import main

        with patch("asynctasq_monitor.cli.main.app", side_effect=RuntimeError("test error")):
            with pytest.raises(RuntimeError, match="test error"):
                main()

    @pytest.mark.unit
    def test_main_returns_0_on_success(self) -> None:
        """Test that main() returns 0 on successful execution."""
        from asynctasq_monitor.__main__ import main

        with patch("asynctasq_monitor.cli.main.app"):
            result = main()
            assert result == 0

    @pytest.mark.unit
    def test_module_if_name_main(self) -> None:
        """Test that the module has proper if __name__ == '__main__' guard."""
        import asynctasq_monitor.__main__ as main_module

        # The module should define a main function
        assert hasattr(main_module, "main")
        assert callable(main_module.main)

        # The module should have the __name__ == "__main__" check in source
        import inspect

        source = inspect.getsource(main_module)
        assert 'if __name__ == "__main__"' in source

    @pytest.mark.unit
    def test_main_returns_130_on_keyboard_interrupt(self) -> None:
        """Test that main() returns 130 on KeyboardInterrupt."""
        from asynctasq_monitor.__main__ import main

        with patch("asynctasq_monitor.cli.main.app", side_effect=KeyboardInterrupt):
            result = main()
            assert result == 130

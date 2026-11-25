"""Tests for logger setup."""
import logging
from unittest.mock import patch


def test_setup_logger_survives_unwritable_log_file(tmp_path):
    """File logging failures must not crash startup."""
    from src import logger as logger_module

    bad_path = str(tmp_path / "file" / "jambot.log")
    (tmp_path / "file").write_text("not a directory")  # makedirs/open will fail

    lg = logging.getLogger('jambot')
    saved = lg.handlers[:]
    try:
        lg.handlers = []
        with patch.object(logger_module.Config, 'LOG_FILE', bad_path):
            result = logger_module.setup_logger()
        assert result is lg
        assert len(result.handlers) == 1  # console only
    finally:
        lg.handlers = saved

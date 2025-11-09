from __future__ import annotations

import logging

from hephaestus.utils import logger as logger_utils


def test_sensitive_data_filter_masks_values() -> None:
    filter_ = logger_utils.SensitiveDataFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="api_key=SECRET123 password: hunter2 token=abcd",
        args=(),
        exc_info=None,
    )
    filter_.filter(record)
    assert "SECRET123" not in record.msg
    assert "hunter2" not in record.msg
    assert "abcd" not in record.msg
    assert record.msg.count("****") >= 3


def test_setup_logger_masks_and_writes_file(tmp_path, caplog) -> None:
    log_file = tmp_path / "hephaestus.log"
    logger = logger_utils.setup_logger("hephaestus.tests.logger", log_file=log_file, level="INFO")

    with caplog.at_level(logging.INFO, logger="hephaestus.tests.logger"):
        logger.info("token: SUPERSECRET")

    assert "SUPERSECRET" not in caplog.text
    assert "****" in caplog.text
    log_content = log_file.read_text(encoding="utf-8")
    assert "SUPERSECRET" not in log_content
    assert "****" in log_content


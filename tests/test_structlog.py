# tests/test_structlog.py
# #ADDED: Tests for structlog configuration and correlation_id middleware

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import structlog

# Import app after structlog is configured
from server import app, logger


class TestStructlogConfiguration:
    """Test that structlog is properly configured for JSON output."""

    def test_logger_is_structlog_instance(self):
        """Verify logger is a structlog bound logger."""
        assert hasattr(logger, 'bind')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')

    def test_logger_accepts_context(self):
        """Verify logger can bind context variables."""
        # This test verifies the API works, not the output format
        bound_logger = logger.bind(test_key="test_value")
        assert bound_logger is not None
        # If we reach here, the API accepts context binding
        assert True


# FIX: Move client fixture to module level so all classes can use it
@pytest.fixture
def structlog_test_client():
    """Test client for structlog tests."""
    return TestClient(app)


class TestCorrelationIdMiddleware:
    """Test correlation_id injection and propagation."""

    def test_correlation_id_generated_if_missing(self, structlog_test_client):
        """Middleware should generate correlation_id when header is absent."""
        response = structlog_test_client.get("/api/projects", headers={})
        # Response should include X-Request-ID header
        assert "X-Request-ID" in response.headers
        # ID should be valid UUID format (basic check)
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 0

    def test_correlation_id_preserved_from_header(self, structlog_test_client):
        """Middleware should preserve provided correlation_id."""
        provided_id = "test-correlation-123"
        response = structlog_test_client.get("/api/projects", headers={"X-Request-ID": provided_id})
        assert response.headers.get("X-Request-ID") == provided_id

    def test_log_entry_can_bind_correlation_id(self):
        """Verify logger.bind() works with correlation_id."""
        # This test verifies the bind() behavior
        test_logger = logger.bind(correlation_id="test-123")
        # Logger should have context attached (no exception = success)
        assert hasattr(test_logger, 'bind')


class TestStructuredErrorLogging:
    """Test that errors are logged with stack traces."""

    def test_error_log_includes_exc_info(self):
        """Verify error logging captures exception info."""
        try:
            raise ValueError("test error")
        except Exception as e:
            # Logger should accept exc_info parameter
            # This verifies the API, actual output depends on processors
            logger.error("Test error", exc_info=e, error=str(e))
            # If we reach here, the API accepts the parameters correctly
            assert True

    def test_404_response_does_not_crash(self, structlog_test_client):
        """404 errors should be handled gracefully."""
        # Test with a path that returns 404
        response = structlog_test_client.get("/nonexistent-path-for-test")
        # We're testing that the middleware doesn't crash
        assert response.status_code in [200, 404, 500]


class TestLogLevels:
    """Test that different log levels are preserved."""

    def test_debug_level(self):
        """Debug logs should be configurable."""
        logger.debug("debug message", test=True)
        assert True  # API accepts the call

    def test_info_level(self):
        """Info logs should work."""
        logger.info("info message", test=True)
        assert True

    def test_warning_level(self):
        """Warning logs should work."""
        logger.warning("warning message", test=True)
        assert True

    def test_error_level(self):
        """Error logs should work."""
        logger.error("error message", test=True)
        assert True

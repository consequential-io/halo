"""
GCS Execution Logger - Logs execution results to Google Cloud Storage.

Logs all Execute Agent actions to GCS for audit trail.
Path: gs://{bucket}/executions/{tenant}/{date}.json
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class GCSExecutionLogger:
    """
    Logger for execution results to Google Cloud Storage.

    Falls back to console logging if GCS is unavailable.
    """

    def __init__(self, bucket: str = "halo-logs", base_path: str = "executions"):
        self.bucket = bucket
        self.base_path = base_path
        self._client = None
        self._gcs_available = False
        self._init_gcs()

    def _init_gcs(self) -> None:
        """Initialize GCS client if available."""
        try:
            from google.cloud import storage
            self._client = storage.Client()
            # Test bucket access
            self._client.get_bucket(self.bucket)
            self._gcs_available = True
            logger.info(f"GCS logger initialized: gs://{self.bucket}/{self.base_path}")
        except ImportError:
            logger.warning("google-cloud-storage not installed, using console logging")
        except Exception as e:
            logger.warning(f"GCS not available ({e}), using console logging")

    def _get_blob_path(self, tenant: str) -> str:
        """Generate blob path for tenant and current date."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"{self.base_path}/{tenant}/{date_str}.json"

    async def log_execution(self, tenant: str, execution: dict[str, Any]) -> dict[str, Any]:
        """
        Log execution result to GCS or console.

        Args:
            tenant: Tenant identifier (e.g., 'TL', 'WH')
            execution: Execution result dict to log

        Returns:
            Log result with path and status
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "timestamp": timestamp,
            "tenant": tenant,
            "execution": execution,
        }

        if self._gcs_available and self._client:
            return await self._log_to_gcs(tenant, log_entry)
        else:
            return self._log_to_console(tenant, log_entry)

    async def _log_to_gcs(self, tenant: str, log_entry: dict) -> dict[str, Any]:
        """Write log entry to GCS (appending to daily file)."""
        try:
            blob_path = self._get_blob_path(tenant)
            bucket = self._client.bucket(self.bucket)
            blob = bucket.blob(blob_path)

            # Read existing content or start fresh
            existing_entries = []
            if blob.exists():
                content = blob.download_as_text()
                existing_entries = json.loads(content)

            existing_entries.append(log_entry)

            # Write back
            blob.upload_from_string(
                json.dumps(existing_entries, indent=2, default=str),
                content_type="application/json"
            )

            gcs_uri = f"gs://{self.bucket}/{blob_path}"
            logger.info(f"Logged execution to {gcs_uri}")

            return {
                "status": "logged",
                "location": gcs_uri,
                "timestamp": log_entry["timestamp"],
            }
        except Exception as e:
            logger.error(f"GCS logging failed: {e}")
            # Fallback to console
            return self._log_to_console(tenant, log_entry)

    def _log_to_console(self, tenant: str, log_entry: dict) -> dict[str, Any]:
        """Fallback: log to console."""
        logger.info(f"[EXECUTION LOG] tenant={tenant}")
        logger.info(json.dumps(log_entry, indent=2, default=str))

        return {
            "status": "logged_console",
            "location": "console",
            "timestamp": log_entry["timestamp"],
        }

    def log_execution_sync(self, tenant: str, execution: dict[str, Any]) -> dict[str, Any]:
        """
        Synchronous version of log_execution.

        For use in non-async contexts.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new task in the running loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.log_execution(tenant, execution)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self.log_execution(tenant, execution))
        except RuntimeError:
            return asyncio.run(self.log_execution(tenant, execution))


# Singleton instance
_logger_instance: GCSExecutionLogger | None = None


def get_execution_logger(bucket: str = "halo-logs") -> GCSExecutionLogger:
    """Get or create the singleton execution logger."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = GCSExecutionLogger(bucket=bucket)
    return _logger_instance

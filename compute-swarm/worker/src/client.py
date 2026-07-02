from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from src.config import Config

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 1.5  # seconds
_REQUEST_TIMEOUT = 30  # seconds


class WorkerClientError(Exception):
    """Base exception for worker client errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WorkerClient:
    """HTTP client that handles all worker-to-orchestrator communication.

    Every request is retried up to three times with exponential backoff.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._session = requests.Session()
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        self._session.headers.update({"Accept": "application/json"})
        if config.api_key:
            self._session.headers.update({"X-Worker-API-Key": config.api_key})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, name: str, capabilities: dict[str, Any]) -> dict[str, Any]:
        """Register a new worker with the orchestrator.

        Returns:
            A dict containing at least ``worker_id`` and ``api_key``.
        """
        payload = {"name": name, "capabilities": capabilities}
        resp = self._request("POST", "/auth/worker-register", json=payload)
        data = resp.json()

        # Persist credentials automatically
        if "worker_id" in data and "api_key" in data:
            self._config.worker_id = data["worker_id"]
            self._config.api_key = data["api_key"]

        return data

    def authenticate(self) -> bool:
        """Verify the stored API key is valid by calling heartbeat.

        Returns ``True`` if the orchestrator accepts the key.
        """
        try:
            self.heartbeat()
            return True
        except WorkerClientError as exc:
            logger.warning("Authentication failed: %s", exc)
            return False

    def heartbeat(self) -> dict[str, Any]:
        """Send a heartbeat with current status and capability snapshot.

        Returns the JSON response from the orchestrator.
        """
        payload = {
            "worker_id": self._config.worker_id,
            "api_key": self._config.api_key,
            "status": "online",  # could be dynamic in future
            "capabilities_snapshot": {},  # caller may enrich if needed
        }
        resp = self._request("POST", "/workers/heartbeat", json=payload)
        return resp.json()

    def claim_unit(self) -> dict[str, Any] | None:
        """Claim a pending work unit from the orchestrator.

        Returns the work unit dict, or ``None`` if no work is available.
        """
        payload = {
            "worker_id": self._config.worker_id,
            "api_key": self._config.api_key,
        }
        try:
            resp = self._request("POST", "/workers/claim-unit", json=payload)
        except WorkerClientError as exc:
            if exc.status_code == 404 or exc.status_code == 204:
                logger.debug("No work units available at this time.")
                return None
            raise

        data = resp.json()
        # API may return nested {"work_unit": {...}} or a flat dict
        work_unit = data.get("work_unit") if isinstance(data, dict) else None
        if work_unit is not None:
            return work_unit
        if not data or ("work_unit_id" not in data and "id" not in data):
            return None
        return data

    def submit_result(
        self,
        work_unit_id: str,
        result_path: str,
        checksum: str,
        logs: str,
        failed: bool = False,
    ) -> dict[str, Any]:
        """Submit a completed result to the orchestrator via multipart upload.

        Args:
            work_unit_id: The UUID of the work unit.
            result_path: Path to the result archive (tar.gz).
            checksum: SHA-256 checksum of the result archive.
            logs: Captured stdout/stderr from the container.
            failed: Whether the container exited with a non-zero code.

        Returns:
            The JSON response from the orchestrator.
        """
        data = {
            "work_unit_id": work_unit_id,
            "api_key": self._config.api_key,
            "checksum": checksum,
            "logs": logs,
            "failed": str(failed).lower(),
        }

        with open(result_path, "rb") as fh:
            files = {
                "result_file": ("result.tar.gz", fh, "application/gzip"),
            }
            resp = self._request("POST", "/workers/submit-result", data=data, files=files)

        return resp.json()

    def get_profile(self) -> dict[str, Any]:
        """Fetch the worker's profile, stats, and reputation from the orchestrator.

        Returns the JSON response.
        """
        params = {
            "worker_id": self._config.worker_id,
            "api_key": self._config.api_key,
        }
        resp = self._request("GET", "/workers/profile", params=params)
        return resp.json()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Execute an HTTP request with retries and backoff."""
        url = f"{self._config.orchestrator_url.rstrip('/')}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            # Reset file pointers for retry so the file is not uploaded empty
            if files and attempt > 1:
                for file_info in files.values():
                    if isinstance(file_info, tuple) and len(file_info) > 1:
                        fh = file_info[1]
                        if hasattr(fh, "seek"):
                            fh.seek(0)
            try:
                resp = self._session.request(
                    method,
                    url,
                    json=json,
                    data=data,
                    files=files,
                    params=params,
                    timeout=_REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                return resp
            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status is not None and 500 <= status < 600:
                    # Retry on 5xx
                    last_exc = exc
                    logger.warning(
                        "Server error %s on %s (attempt %d/%d)",
                        status,
                        path,
                        attempt,
                        _MAX_RETRIES,
                    )
                elif status == 429:
                    # Retry on rate limit
                    last_exc = exc
                    logger.warning(
                        "Rate limited on %s (attempt %d/%d)",
                        path,
                        attempt,
                        _MAX_RETRIES,
                    )
                else:
                    # 4xx errors are not retried
                    raise WorkerClientError(
                        f"HTTP {status}: {exc.response.text if exc.response else ''}",
                        status_code=status,
                    )
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as exc:
                last_exc = exc
                logger.warning(
                    "Network error on %s (attempt %d/%d): %s",
                    path,
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )

            if attempt < _MAX_RETRIES:
                sleep_time = _BACKOFF_BASE * (2 ** (attempt - 1))
                logger.info("Retrying in %.1f seconds...", sleep_time)
                time.sleep(sleep_time)

        raise WorkerClientError(
            f"Request to {path} failed after {_MAX_RETRIES} attempts: {last_exc}"
        )

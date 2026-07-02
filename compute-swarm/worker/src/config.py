from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import appdirs
from dotenv import load_dotenv


APP_NAME = "computeswarm"
APP_AUTHOR = "computeswarm"


class Config:
    """Cross-platform configuration manager for the ComputeSwarm worker client.

    Reads from ``~/.computeswarm/config.json`` (platform-specific) and
    environment variables. Environment variables take precedence.
    """

    _defaults: dict[str, Any] = {
        "orchestrator_url": "https://api.computeswarm.local",
        "worker_id": None,
        "api_key": None,
        "worker_name": None,
        "max_cpu_percent": 80,
        "max_ram_percent": 75,
        "job_timeout_seconds": 3600,
        "idle_detection": "always_run",
        "data_dir": None,
    }

    def __init__(self) -> None:
        load_dotenv()

        self._config_dir = Path(appdirs.user_config_dir(APP_NAME, APP_AUTHOR))
        self._config_file = self._config_dir / "config.json"
        self._data_dir = Path(appdirs.user_data_dir(APP_NAME, APP_AUTHOR))

        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._values: dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any:
        """Return the current value for *key*."""
        return self._values.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set *key* to *value* and persist to disk."""
        self._values[key] = value
        self._save()

    def update(self, updates: dict[str, Any]) -> None:
        """Bulk update and persist."""
        self._values.update(updates)
        self._save()

    @property
    def orchestrator_url(self) -> str:
        return self._ensure_str(self.get("orchestrator_url"))

    @orchestrator_url.setter
    def orchestrator_url(self, value: str) -> None:
        self.set("orchestrator_url", value)

    @property
    def worker_id(self) -> str | None:
        v = self.get("worker_id")
        return str(v) if v is not None else None

    @worker_id.setter
    def worker_id(self, value: str | None) -> None:
        self.set("worker_id", value)

    @property
    def api_key(self) -> str | None:
        v = self.get("api_key")
        return str(v) if v is not None else None

    @api_key.setter
    def api_key(self, value: str | None) -> None:
        self.set("api_key", value)

    @property
    def worker_name(self) -> str | None:
        v = self.get("worker_name")
        return str(v) if v is not None else None

    @worker_name.setter
    def worker_name(self, value: str | None) -> None:
        self.set("worker_name", value)

    @property
    def max_cpu_percent(self) -> int:
        return int(self.get("max_cpu_percent") or 80)

    @max_cpu_percent.setter
    def max_cpu_percent(self, value: int) -> None:
        self.set("max_cpu_percent", int(value))

    @property
    def max_ram_percent(self) -> int:
        return int(self.get("max_ram_percent") or 75)

    @max_ram_percent.setter
    def max_ram_percent(self, value: int) -> None:
        self.set("max_ram_percent", int(value))

    @property
    def job_timeout_seconds(self) -> int:
        return int(self.get("job_timeout_seconds") or 3600)

    @job_timeout_seconds.setter
    def job_timeout_seconds(self, value: int) -> None:
        self.set("job_timeout_seconds", int(value))

    @property
    def idle_detection(self) -> str:
        return self._ensure_str(self.get("idle_detection") or "always_run")

    @idle_detection.setter
    def idle_detection(self, value: str) -> None:
        self.set("idle_detection", value)

    @property
    def data_dir(self) -> Path:
        v = self.get("data_dir")
        if v is not None:
            return Path(v)
        return self._data_dir

    @data_dir.setter
    def data_dir(self, value: str | Path) -> None:
        self.set("data_dir", str(value))

    def as_dict(self) -> dict[str, Any]:
        """Return a shallow copy of the current configuration."""
        return dict(self._values)

    def save(self) -> None:
        """Persist current values to disk."""
        self._save()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load from JSON file, then overlay environment variables."""
        # 1. Start with defaults
        values = dict(self._defaults)

        # 2. Overlay config file if present
        if self._config_file.exists():
            try:
                with self._config_file.open("r", encoding="utf-8") as fh:
                    file_data = json.load(fh)
                if isinstance(file_data, dict):
                    values.update(file_data)
            except (json.JSONDecodeError, OSError) as exc:
                # Log warning but continue with defaults + env
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to read config file %s: %s", self._config_file, exc
                )

        # 3. Overlay environment variables (highest priority)
        env_map = {
            "orchestrator_url": "ORCHESTRATOR_URL",
            "worker_id": "WORKER_ID",
            "api_key": "WORKER_API_KEY",
            "worker_name": "WORKER_NAME",
            "max_cpu_percent": "MAX_CPU_PERCENT",
            "max_ram_percent": "MAX_RAM_PERCENT",
            "job_timeout_seconds": "JOB_TIMEOUT_SECONDS",
            "idle_detection": "IDLE_DETECTION",
            "data_dir": "DATA_DIR",
        }
        for key, env_var in env_map.items():
            val = os.getenv(env_var)
            if val is not None and val != "":
                values[key] = val

        # 4. Coerce types
        for int_key in ("max_cpu_percent", "max_ram_percent", "job_timeout_seconds"):
            if values.get(int_key) is not None:
                try:
                    values[int_key] = int(values[int_key])
                except (TypeError, ValueError):
                    values[int_key] = self._defaults[int_key]

        self._values = values

    def _save(self) -> None:
        """Persist current values to ``config.json``."""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with self._config_file.open("w", encoding="utf-8") as fh:
                json.dump(self._values, fh, indent=2, default=str)
        except OSError as exc:
            import logging
            logging.getLogger(__name__).error(
                "Failed to write config file %s: %s", self._config_file, exc
            )

    @staticmethod
    def _ensure_str(value: Any) -> str:
        return str(value) if value is not None else ""

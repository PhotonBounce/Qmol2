from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import docker
import docker.errors
import docker.types
import psutil
from docker.models.containers import Container

from src.config import Config

logger = logging.getLogger(__name__)


class DockerRunnerError(Exception):
    """Raised when a Docker operation fails."""


class DockerRunner:
    """Manages Docker image pulls, container execution, and cleanup."""

    def __init__(self, config: Config) -> None:
        self._config = config
        try:
            self._client = docker.from_env()
            self._client.ping()
        except docker.errors.DockerException as exc:
            raise DockerRunnerError(
                "Could not connect to Docker daemon. "
                "Is Docker installed and running?"
            ) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def pull_image(self, image: str) -> None:
        """Pull a Docker image if it doesn't already exist locally, logging progress."""
        try:
            self._client.images.get(image)
            logger.info("Image %s already exists locally; skipping pull.", image)
            return
        except docker.errors.ImageNotFound:
            pass  # Image not present locally, proceed to pull

        logger.info("Pulling image %s ...", image)
        try:
            for line in self._client.api.pull(image, stream=True, decode=True):
                if isinstance(line, dict):
                    status = line.get("status", "")
                    progress = line.get("progress", "")
                    if progress:
                        logger.debug("%s %s", status, progress)
                    elif status:
                        logger.debug("%s", status)
        except docker.errors.ImageNotFound:
            raise DockerRunnerError(f"Image not found: {image}")
        except docker.errors.APIError as exc:
            raise DockerRunnerError(f"Failed to pull image {image}: {exc}") from exc

    def run_container(
        self,
        image: str,
        command: str | list[str] | None = None,
        env_vars: dict[str, str] | None = None,
        input_dir: str | Path | None = None,
        output_dir: str | Path | None = None,
        cpu_limit: float | None = None,
        ram_limit: str | None = None,
        gpu: bool = False,
        timeout: int | None = None,
    ) -> tuple[int, str, str, Path, str]:
        """Run a Docker container with resource limits and volume mounts.

        Args:
            image: Docker image reference.
            command: Command override (string or list).
            env_vars: Environment variables for the container.
            input_dir: Host path to mount at ``/workspace/input``.
            output_dir: Host path to mount at ``/workspace/output``.
            cpu_limit: Number of CPU cores to allocate (e.g. ``2.0``).
            ram_limit: Memory limit (e.g. ``4g`` or ``4096m``).
            gpu: Whether to pass through GPU devices.
            timeout: Maximum runtime in seconds (``None`` = no timeout).

        Returns:
            A tuple of ``(exit_code, stdout, stderr, output_dir, container_id)``.
        """
        # Ensure output directory exists
        output_path = Path(output_dir) if output_dir else Path(self._config.data_dir) / "output"
        output_path.mkdir(parents=True, exist_ok=True)

        # Build mounts
        mounts: dict[str, dict[str, str]] = {}
        if input_dir is not None:
            input_path = Path(input_dir)
            input_path.mkdir(parents=True, exist_ok=True)
            mounts[str(input_path)] = {"bind": "/workspace/input", "mode": "ro"}
        mounts[str(output_path)] = {"bind": "/workspace/output", "mode": "rw"}

        # Build host config kwargs
        host_config: dict[str, Any] = {
            "network_mode": "none",
            "auto_remove": False,  # we clean up manually
            "binds": mounts,
        }

        if cpu_limit is not None and cpu_limit > 0:
            host_config["nano_cpus"] = int(cpu_limit * 1e9)

        if ram_limit is not None:
            host_config["mem_limit"] = ram_limit

        if gpu and self.has_gpu():
            host_config["device_requests"] = [
                docker.types.DeviceRequest(count=-1, capabilities=["gpu"])
            ]
            logger.info("GPU passthrough enabled for this container.")

        # Normalize command
        cmd = command
        if isinstance(cmd, str):
            cmd = ["sh", "-c", cmd]

        env = env_vars or {}
        env.setdefault("COMPUTESWARM", "1")

        logger.info(
            "Running container: image=%s cmd=%s cpu=%s ram=%s gpu=%s timeout=%s",
            image,
            cmd,
            cpu_limit,
            ram_limit,
            gpu,
            timeout,
        )

        try:
            container: Container = self._client.containers.create(
                image=image,
                command=cmd,
                environment=env,
                **host_config,
            )
        except docker.errors.ImageNotFound:
            raise DockerRunnerError(f"Image {image} not found locally.")
        except docker.errors.APIError as exc:
            raise DockerRunnerError(f"Failed to create container: {exc}") from exc

        container.start()
        logger.info("Container %s started.", container.short_id)

        try:
            if timeout is not None and timeout > 0:
                try:
                    result = container.wait(timeout=timeout)
                except docker.errors.RequestTimeout:
                    logger.warning("Container %s exceeded timeout (%ss). Killing...", container.short_id, timeout)
                    container.kill(signal="SIGKILL")
                    result = container.wait()
            else:
                result = container.wait()

            exit_code = result.get("StatusCode", -1)
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
        except docker.errors.APIError as exc:
            raise DockerRunnerError(f"Error while waiting for container: {exc}") from exc
        finally:
            # Cleanup is deferred to the caller via ``cleanup_container``
            pass

        return exit_code, stdout, stderr, output_path, container.id

    def cleanup_container(self, container_id: str) -> None:
        """Remove a container and its associated volumes."""
        logger.debug("Cleaning up container %s", container_id)
        try:
            container = self._client.containers.get(container_id)
            container.remove(force=True, v=True)
        except docker.errors.NotFound:
            logger.debug("Container %s already removed.", container_id)
        except docker.errors.APIError as exc:
            logger.warning("Failed to remove container %s: %s", container_id, exc)

    def has_gpu(self) -> bool:
        """Detect whether an NVIDIA GPU and the nvidia-docker runtime are available."""
        # Quick check: look for nvidia-smi on PATH
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return False

        try:
            subprocess.run(
                [nvidia_smi, "-L"],
                capture_output=True,
                check=True,
                timeout=10,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

        # Check Docker can actually use the nvidia runtime
        try:
            info = self._client.info()
            runtimes = info.get("Runtimes", {})
            if "nvidia" in runtimes:
                return True
        except docker.errors.APIError:
            pass

        # Fallback: check if nvidia-docker runtime is available via info
        try:
            info = self._client.info()
            # Some installations expose nvidia as a default runtime or via swarm labels
            default_runtime = info.get("DefaultRuntime", "")
            if "nvidia" in default_runtime:
                return True
        except docker.errors.APIError:
            pass

        return False

    def get_system_capabilities(self) -> dict[str, Any]:
        """Return a snapshot of the host system capabilities."""
        cpu_cores = psutil.cpu_count(logical=True)
        ram_bytes = psutil.virtual_memory().total
        ram_gb = round(ram_bytes / (1024**3), 2)

        gpu_available = self.has_gpu()
        gpu_model: str | None = None
        if gpu_available:
            gpu_model = self._detect_gpu_model()

        docker_version = "unknown"
        try:
            version_info = self._client.version()
            docker_version = version_info.get("Version", "unknown")
        except docker.errors.APIError:
            pass

        return {
            "cpu_cores": cpu_cores,
            "ram_gb": ram_gb,
            "gpu_available": gpu_available,
            "gpu_model": gpu_model,
            "os": sys.platform,
            "docker_version": docker_version,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_gpu_model(self) -> str | None:
        """Attempt to read the GPU model name from nvidia-smi."""
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return None
        try:
            proc = subprocess.run(
                [nvidia_smi, "-L"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            # nvidia-smi -L returns lines like:
            # GPU 0: NVIDIA GeForce RTX 3080 (UUID: ...)
            first_line = proc.stdout.strip().splitlines()[0]
            if ":" in first_line:
                return first_line.split(":", 1)[1].split("(")[0].strip()
            return first_line.strip()
        except (subprocess.CalledProcessError, IndexError, subprocess.TimeoutExpired):
            return None

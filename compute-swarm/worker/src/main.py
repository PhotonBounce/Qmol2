from __future__ import annotations

import hashlib
import logging
import logging.handlers
import shutil
import signal
import sys
import tarfile
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import click
import requests

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

from src.client import WorkerClient, WorkerClientError
from src.config import Config
from src.docker_runner import DockerRunner, DockerRunnerError

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

_SHUTDOWN_EVENT = threading.Event()

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _setup_logging(data_dir: Path) -> None:
    """Configure root logger to write to console and a rotating file."""
    log_dir = data_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "worker.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """ComputeSwarm Worker Client — run scientific jobs on your hardware."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config()


@cli.command()
@click.option("--name", prompt="Worker name", help="Human-readable worker name.")
@click.option("--orchestrator-url", prompt="Orchestrator URL", help="Base URL of the orchestrator API.")
@click.pass_context
def register(ctx: click.Context, name: str, orchestrator_url: str) -> None:
    """Interactive registration — detect capabilities and register with the orchestrator."""
    config: Config = ctx.obj["config"]
    config.orchestrator_url = orchestrator_url
    config.worker_name = name

    # Detect capabilities
    try:
        runner = DockerRunner(config)
        capabilities = runner.get_system_capabilities()
    except DockerRunnerError as exc:
        click.echo(f"Docker setup failed: {exc}", err=True)
        sys.exit(1)
    click.echo(f"Detected capabilities: {capabilities}")

    client = WorkerClient(config)
    try:
        result = client.register(name=name, capabilities=capabilities)
    except WorkerClientError as exc:
        click.echo(f"Registration failed: {exc}", err=True)
        sys.exit(1)

    config.worker_id = result.get("worker_id")
    config.api_key = result.get("api_key")
    config.save()
    click.echo(f"Worker registered successfully!")
    click.echo(f"  Worker ID : {config.worker_id}")
    click.echo(f"  API Key   : {'*' * 12} (saved to config)")


@cli.command()
@click.pass_context
def start(ctx: click.Context) -> None:
    """Start the worker daemon loop."""
    config: Config = ctx.obj["config"]
    _setup_logging(config.data_dir)
    logger = logging.getLogger(__name__)

    # Validate credentials
    if not config.worker_id or not config.api_key:
        click.echo("Worker not registered. Run 'register' first.", err=True)
        sys.exit(1)

    client = WorkerClient(config)
    try:
        runner = DockerRunner(config)
    except DockerRunnerError as exc:
        logger.error("Docker setup failed: %s", exc)
        click.echo(f"Docker setup failed: {exc}", err=True)
        sys.exit(1)

    logger.info("Starting worker daemon (name=%s)", config.worker_name)

    # Authenticate
    click.echo("Authenticating with orchestrator ...")
    if not client.authenticate():
        click.echo("Authentication failed. Check your API key and orchestrator URL.", err=True)
        sys.exit(1)
    click.echo("Authenticated successfully.")

    # Install signal handlers
    def _on_signal(signum: int, _frame: Any) -> None:
        logger.info("Received signal %s, initiating graceful shutdown ...", signal.Signals(signum).name)
        _SHUTDOWN_EVENT.set()

    signal.signal(signal.SIGINT, _on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _on_signal)

    # Main loop
    last_heartbeat = 0.0
    heartbeat_interval = 15.0
    idle_sleep = 5.0

    while not _SHUTDOWN_EVENT.is_set():
        try:
            now = time.monotonic()

            # Heartbeat
            work_unit = None
            if now - last_heartbeat >= heartbeat_interval:
                logger.debug("Sending heartbeat ...")
                try:
                    heartbeat_resp = client.heartbeat()
                    # If heartbeat returns a work unit, skip claim_unit
                    work_unit = heartbeat_resp.get("work_unit") if isinstance(heartbeat_resp, dict) else None
                except WorkerClientError as exc:
                    logger.warning("Heartbeat failed: %s", exc)
                last_heartbeat = now

            # Claim work (only if heartbeat didn't return one)
            if work_unit is None:
                try:
                    work_unit = client.claim_unit()
                except WorkerClientError as exc:
                    logger.warning("Claim unit failed: %s", exc)

            if work_unit is not None:
                _process_work_unit(config, client, runner, work_unit)
                continue

            # Idle wait
            _SHUTDOWN_EVENT.wait(idle_sleep)

        except Exception as exc:
            logger.exception("Unexpected error in main loop: %s", exc)
            _SHUTDOWN_EVENT.wait(idle_sleep)

    logger.info("Worker daemon shut down gracefully.")
    click.echo("Shutdown complete.")


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Print current worker profile and status."""
    config: Config = ctx.obj["config"]
    if not config.worker_id or not config.api_key:
        click.echo("Worker not registered.", err=True)
        sys.exit(1)

    client = WorkerClient(config)
    try:
        profile = client.get_profile()
    except WorkerClientError as exc:
        click.echo(f"Failed to fetch profile: {exc}", err=True)
        sys.exit(1)

    click.echo("─" * 40)
    click.echo(f"Worker ID    : {config.worker_id}")
    click.echo(f"Worker Name  : {config.worker_name}")
    click.echo(f"Orchestrator : {config.orchestrator_url}")
    for key, value in profile.items():
        click.echo(f"{key:12s} : {value}")
    click.echo("─" * 40)


@cli.command()
@click.pass_context
def config_cmd(ctx: click.Context) -> None:
    """Print current local configuration."""
    config: Config = ctx.obj["config"]
    click.echo("─" * 40)
    for key, value in config.as_dict().items():
        click.echo(f"{key:20s} : {value}")
    click.echo("─" * 40)


# ---------------------------------------------------------------------------
# Work unit processing
# ---------------------------------------------------------------------------


def _process_work_unit(
    config: Config,
    client: WorkerClient,
    runner: DockerRunner,
    work_unit: dict[str, Any],
) -> None:
    """Download input, run Docker, upload result, and clean up."""
    logger = logging.getLogger(__name__)

    work_unit_id = work_unit.get("work_unit_id") or work_unit.get("id")
    job_id = work_unit.get("job_id")
    docker_image = work_unit.get("docker_image")
    command = work_unit.get("command")
    env_vars = work_unit.get("env_vars", {})
    input_artifact_url = work_unit.get("input_artifact_url")
    cpu_limit = work_unit.get("cpu_limit")
    ram_limit = work_unit.get("ram_limit")
    gpu_required = work_unit.get("gpu", False)
    timeout = work_unit.get("timeout", config.job_timeout_seconds)

    logger.info(
        "Processing work unit %s (job=%s, image=%s)",
        work_unit_id,
        job_id,
        docker_image,
    )

    work_dir = config.data_dir / "jobs" / str(work_unit_id)
    input_dir = work_dir / "input"
    output_dir = work_dir / "output"
    result_archive = work_dir / "result.tar.gz"

    container_id: str | None = None
    try:
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Download input artifact
        if input_artifact_url:
            logger.info("Downloading input artifact ...")
            _download_artifact(input_artifact_url, input_dir)

        # 2. Pull image
        runner.pull_image(docker_image)

        # 3. Calculate resource limits
        if cpu_limit is None:
            cpu_limit = _calculate_cpu_limit(config)
        if ram_limit is None:
            ram_limit = _calculate_ram_limit(config)

        # 4. Run container
        exit_code, stdout, stderr, _output_dir, container_id = runner.run_container(
            image=docker_image,
            command=command,
            env_vars=env_vars,
            input_dir=input_dir,
            output_dir=output_dir,
            cpu_limit=cpu_limit,
            ram_limit=ram_limit,
            gpu=gpu_required,
            timeout=timeout,
        )

        logs = f"--- STDOUT ---\n{stdout}\n--- STDERR ---\n{stderr}"

        if exit_code != 0:
            logger.error("Container exited with code %s for unit %s", exit_code, work_unit_id)
            # We still submit the result so the orchestrator knows it failed
        else:
            logger.info("Container finished successfully for unit %s", work_unit_id)

        # 5. Package output
        logger.info("Packaging output ...")
        _create_tarball(output_dir, result_archive)

        # 6. Compute checksum
        checksum = _sha256_file(result_archive)

        # 7. Submit result
        logger.info("Submitting result for unit %s ...", work_unit_id)
        client.submit_result(
            work_unit_id=str(work_unit_id),
            result_path=str(result_archive),
            checksum=checksum,
            logs=logs,
            failed=(exit_code != 0),
        )
        logger.info("Result submitted for unit %s.", work_unit_id)

    except WorkerClientError as exc:
        logger.error("WorkerClient error during unit %s: %s", work_unit_id, exc)
    except DockerRunnerError as exc:
        logger.error("DockerRunner error during unit %s: %s", work_unit_id, exc)
    except Exception as exc:
        logger.exception("Unexpected error during unit %s: %s", work_unit_id, exc)
    finally:
        # 8. Clean up container
        if container_id:
            logger.info("Cleaning up container %s ...", container_id)
            try:
                runner.cleanup_container(container_id)
            except Exception as exc:
                logger.warning("Failed to clean up container %s: %s", container_id, exc)

        # 9. Clean up local files
        logger.info("Cleaning up local files for unit %s ...", work_unit_id)
        try:
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
        except OSError as exc:
            logger.warning("Failed to clean up work directory %s: %s", work_dir, exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _download_artifact(url: str, destination_dir: Path) -> None:
    """Download a tar.gz artifact and extract it into *destination_dir*."""
    logger = logging.getLogger(__name__)
    max_retries = 3
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, stream=True, timeout=120)
            resp.raise_for_status()
            break
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status is not None and 500 <= status < 600:
                last_exc = exc
                logger.warning(
                    "Download failed with server error %s (attempt %d/%d)",
                    status,
                    attempt,
                    max_retries,
                )
                if attempt < max_retries:
                    time.sleep(1.5 * (2 ** (attempt - 1)))
                continue
            raise WorkerClientError(
                f"Download failed: HTTP {status}: {exc.response.text if exc.response else ''}",
                status_code=status,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_exc = exc
            logger.warning(
                "Download network error (attempt %d/%d): %s",
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                time.sleep(1.5 * (2 ** (attempt - 1)))
            continue
    else:
        raise WorkerClientError(
            f"Download failed after {max_retries} attempts: {last_exc}"
        )

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        for chunk in resp.iter_content(chunk_size=8192):
            tmp.write(chunk)
        tmp_path = Path(tmp.name)

    try:
        with tarfile.open(tmp_path, "r:gz") as tar:
            tar.extractall(path=destination_dir)
        logger.info("Extracted artifact to %s", destination_dir)
    finally:
        tmp_path.unlink(missing_ok=True)


def _create_tarball(source_dir: Path, tarball_path: Path) -> None:
    """Create a gzipped tar archive of *source_dir*."""
    with tarfile.open(tarball_path, "w:gz") as tar:
        for entry in source_dir.rglob("*"):
            tar.add(entry, arcname=entry.relative_to(source_dir))


def _sha256_file(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _calculate_cpu_limit(config: Config) -> float:
    """Return the number of CPU cores this worker is allowed to use."""
    if psutil is None:
        raise RuntimeError(
            "psutil is required for automatic CPU limit calculation. "
            "Install it or set cpu_limit manually."
        )
    total = psutil.cpu_count(logical=True) or 1
    return max(1.0, round(total * (config.max_cpu_percent / 100), 1))


def _calculate_ram_limit(config: Config) -> str:
    """Return the RAM limit string for Docker (e.g. ``4g``)."""
    if psutil is None:
        raise RuntimeError(
            "psutil is required for automatic RAM limit calculation. "
            "Install it or set ram_limit manually."
        )
    total_gb = psutil.virtual_memory().total / (1024**3)
    limit_gb = max(1, int(total_gb * (config.max_ram_percent / 100)))
    return f"{limit_gb}g"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()

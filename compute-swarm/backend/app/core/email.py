import logging
from typing import Any

# TODO: Configure SMTP settings for production (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
# from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to: str,
    subject: str,
    body: str,
    html: str | None = None,
    from_addr: str = "noreply@computeswarm.local",
) -> None:
    """Stub email sender. Logs to console. Replace with aiosmtplib or fastapi-mail in production."""
    logger.info("=" * 60)
    logger.info("[EMAIL] To: %s | Subject: %s", to, subject)
    logger.info("[EMAIL] From: %s", from_addr)
    if html:
        logger.info("[EMAIL] HTML: %s", html[:200])
    logger.info("[EMAIL] Body: %s", body)
    logger.info("=" * 60)


async def notify_job_completed(user_email: str, job_name: str) -> None:
    subject = f"Job completed: {job_name}"
    body = (
        f"Hi,\n\n"
        f"Your job '{job_name}' has completed successfully.\n"
        f"You can download the results from the ComputeSwarm dashboard.\n\n"
        f"Thanks for using ComputeSwarm!\n"
    )
    html = f"""
    <html>
      <body>
        <h2>Job Completed</h2>
        <p>Your job <strong>{job_name}</strong> has completed successfully.</p>
        <p>You can download the results from the <a href="#">ComputeSwarm dashboard</a>.</p>
        <p>Thanks for using ComputeSwarm!</p>
      </body>
    </html>
    """
    await send_email(user_email, subject, body, html=html)


async def notify_worker_banned(worker_email: str, reason: str = "Violation of platform policies") -> None:
    subject = "ComputeSwarm: Worker banned"
    body = (
        f"Hi,\n\n"
        f"Your worker has been banned from the ComputeSwarm platform.\n"
        f"Reason: {reason}\n\n"
        f"If you believe this is a mistake, please contact support.\n"
    )
    html = f"""
    <html>
      <body>
        <h2>Worker Banned</h2>
        <p>Your worker has been banned from the ComputeSwarm platform.</p>
        <p>Reason: <strong>{reason}</strong></p>
        <p>If you believe this is a mistake, please contact support.</p>
      </body>
    </html>
    """
    await send_email(worker_email, subject, body, html=html)


async def notify_low_credits(user_email: str, balance: float) -> None:
    subject = "ComputeSwarm: Low credits warning"
    body = (
        f"Hi,\n\n"
        f"Your credit balance is running low: {balance:.2f} credits remaining.\n"
        f"Purchase more credits to keep your jobs running uninterrupted.\n\n"
        f"Thanks for using ComputeSwarm!\n"
    )
    html = f"""
    <html>
      <body>
        <h2>Low Credits Warning</h2>
        <p>Your credit balance is running low: <strong>{balance:.2f}</strong> credits remaining.</p>
        <p>Purchase more credits to keep your jobs running uninterrupted.</p>
        <p>Thanks for using ComputeSwarm!</p>
      </body>
    </html>
    """
    await send_email(user_email, subject, body, html=html)

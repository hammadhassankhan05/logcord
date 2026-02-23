import logging
import sys
from .handler import DiscordWebhookHandler


def setup_logger(
    name: str,
    webhook_url: str = None,
    console_level: str = "INFO",  # Changed to string defaults
    discord_level: str = "WARNING",  # Changed to string defaults
    console_format: str = "%(asctime)s | %(levelname)s | %(message)s",
    discord_format: str = "%(levelname)s: %(message)s",
) -> logging.Logger:
    """
    Quickly configures a dual-logger that outputs to the console and a Discord webhook.
    """
    logger = logging.getLogger(name)

    # Safely convert string levels (e.g., "INFO") to their integer equivalents
    c_level = (
        logging.getLevelName(console_level.upper())
        if isinstance(console_level, str)
        else console_level
    )
    d_level = (
        logging.getLevelName(discord_level.upper())
        if isinstance(discord_level, str)
        else discord_level
    )

    # Set the base logger to the lowest level required
    logger.setLevel(min(c_level, d_level))

    # Prevent duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # 1. Setup Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(c_level)
    console_handler.setFormatter(logging.Formatter(console_format))
    logger.addHandler(console_handler)

    # 2. Setup Discord Handler
    if webhook_url:
        discord_handler = DiscordWebhookHandler(webhook_url)
        discord_handler.setLevel(d_level)
        discord_handler.setFormatter(logging.Formatter(discord_format))
        logger.addHandler(discord_handler)
    else:
        logger.warning("No webhook_url provided. Logcord will only log to the console.")

    return logger


def shutdown_logs():
    """
    Gracefully shuts down all loggers and ensures the background Discord
    thread finishes sending any remaining logs in the queue before exit.
    """
    logging.shutdown()


# Expose only what the user needs
__all__ = ["setup_logger", "shutdown_logs", "DiscordWebhookHandler"]

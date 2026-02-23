# Discord Webhook Logger 📝👾

A lightweight, thread-safe Python logging handler that streams your application logs directly to a Discord channel using Webhooks. 

Perfect for monitoring background tasks, web scrapers, automated pipelines, or server alerts without needing heavy monitoring infrastructure.

## Installation

```bash
pip install logcord
```

# Quick Start
```python
import logging
from logcord.handler import DiscordWebhookHandler
```

## How It Works Under the Hood

The `DiscordWebhookHandler` is designed to have zero impact on your main application's performance.

1. **Non-Blocking Execution:** When you call `logger.info()`, the handler immediately places the formatted message into a thread-safe `queue.Queue` and returns control to your application. 
2. **Background Processing:** A daemon thread runs in the background, waking up every `flush_interval` (default 3 seconds) to pull all pending logs from the queue.
3. **Smart Batching & Chunking:** The background worker stitches multiple short logs together into a single message to minimize HTTP requests. If a single log (like a massive traceback) exceeds Discord's character limit, it automatically chunks it into multiple sequential messages.
4. **Rate Limit Handling:** If Discord returns a HTTP `429 Too Many Requests` status, the handler pauses execution for the exact `retry_after` period requested by Discord before continuing, ensuring no logs are dropped.

## Advanced Usage: Dual Logging

For production scripts like web scraping pipelines, automated pricing tools, or forecasting systems, you typically want to log to the console for local debugging, while sending only critical warnings and errors to Discord. 

Here is how you configure the handler to only forward `WARNING` level and above to Discord:

```python
import os
from logcord import setup_logger, shutdown

# 1. Setup logger using simple strings
webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
logger = setup_logger(
    name="AutomationApp", 
    webhook_url=webhook_url,
    console_level="DEBUG",
    discord_level="ERROR"
)

# 2. Use standard logging methods directly
logger.info("Script started.")
logger.error("Something went wrong!")

# 3. Call logcord's custom shutdown wrapper
shutdown_logs()
```
import logging
import threading
import queue
import time
import requests


class DiscordWebhookHandler(logging.Handler):
    """
    A custom logging handler that batches and sends logs to a Discord Webhook.
    """

    def __init__(
        self,
        webhook_url: str,
        flush_interval: float = 3.0,
        max_chars: int = 1900,
        message_format: str = "text",
    ):
        """
        Initializes the handler with the given webhook URL and configuration.

        Args:
            webhook_url: The Discord webhook URL to send logs to.
            flush_interval: How often (in seconds) to flush the log queue. Defaults to 3.0.
            max_chars: Maximum characters per Discord message. Defaults to 1900 (Discord limit is 2000).
            message_format: Format for message content: "text" or "code". Defaults to "text".
        """
        super().__init__()
        self.webhook_url = webhook_url
        self.flush_interval = flush_interval
        # Discord limit is 2000; keeping it at 1900 allows room for formatting
        self.max_chars = max_chars
        self.message_format = message_format
        self._log_queue = queue.Queue()
        self._stop_event = threading.Event()

        # Start background thread for sending logs
        self._worker_thread = threading.Thread(
            target=self._flushing_worker, daemon=True
        )
        self._worker_thread.start()

    def emit(self, record: logging.LogRecord):
        """Puts the formatted log record into the queue for the worker thread."""
        try:
            msg = self.format(record)
            self._log_queue.put(msg)
        except Exception:
            self.handleError(record)

    def _flushing_worker(self):
        """Background worker that flushes the queue at set intervals."""
        while not self._stop_event.is_set():
            self._flush_queue()
            # Wait for the interval, but wake up immediately if stop_event is set
            self._stop_event.wait(self.flush_interval)

        # Ensure the queue is fully drained on shutdown
        self._flush_queue()

    def _flush_queue(self):
        """Pulls all pending logs from the queue and batches them."""
        messages = []
        while not self._log_queue.empty():
            try:
                messages.append(self._log_queue.get_nowait())
            except queue.Empty:
                break

        if not messages:
            return

        current_batch = []
        current_len = 0

        for msg in messages:
            msg_len = len(msg) + 1  # +1 accounts for the newline character

            if msg_len > self.max_chars:
                # Flush existing batch first before handling the massive log
                if current_batch:
                    self._send_payload("\n".join(current_batch))
                    current_batch = []
                    current_len = 0

                # Chunk and send the oversized message
                for i in range(0, len(msg), self.max_chars):
                    self._send_payload(msg[i : i + self.max_chars])

            elif current_len + msg_len > self.max_chars:
                # Batch is full; flush it and start a new one
                self._send_payload("\n".join(current_batch))
                current_batch = [msg]
                current_len = msg_len

            else:
                # Add to current batch
                current_batch.append(msg)
                current_len += msg_len

        # Flush any remaining logs in the final batch
        if current_batch:
            self._send_payload("\n".join(current_batch))

    def _send_payload(self, content: str):
        """Handles the HTTP POST request to Discord."""
        if not content:
            return

            # Wrap in a code block for cleaner formatting in Discord
        if self.message_format == "code":
            payload = {"content": f"```\n{content}\n```"}
        elif self.message_format == "text":
            payload = {"content": f"\n{content}\n"}

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)

            if response.status_code == 429:
                # Rate limited: sleep for the required time and retry exactly once
                retry_after = response.json().get("retry_after", 3)
                time.sleep(retry_after)
                requests.post(self.webhook_url, json=payload, timeout=10)
            elif response.status_code >= 400:
                print(
                    f"DiscordHandler HTTP Error: {response.status_code} - {response.text}"
                )

        except Exception as e:
            print(f"DiscordHandler Network Error: {e}")

    def close(self):
        """
        Overrides logging.Handler.close to ensure graceful shutdown and final flushing.
        """
        self._stop_event.set()
        if self._worker_thread.is_alive():
            # Give the thread time to finish its final flush
            self._worker_thread.join(timeout=self.flush_interval + 2)
        super().close()

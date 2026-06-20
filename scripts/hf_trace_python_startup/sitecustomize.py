"""Python startup customisations for HF trace helper processes."""

from __future__ import annotations

import warnings


warnings.filterwarnings(
    "ignore",
    message=r"resource_tracker: There appear to be .* leaked semaphore objects to clean up at shutdown",
    category=UserWarning,
    module="multiprocessing.resource_tracker",
)

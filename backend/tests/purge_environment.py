# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a process that purges reads to reach the object storage of the tests."""

import os
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from waterfall.platform.storage import Bucket


def storage_environment(bucket: Bucket) -> dict[str, str]:
    """Give the variables that make a process reach the bucket of the tests, as the purge reads."""
    parts = urlsplit(os.environ["WATERFALL_TEST_STORAGE_URL"])
    return {
        "WATERFALL_STORAGE_ADDRESS": f"{parts.scheme}://{parts.hostname}:{parts.port}",
        "WATERFALL_STORAGE_ACCESS_KEY": parts.username or "",
        "WATERFALL_STORAGE_SECRET": parts.password or "",
        "WATERFALL_BACKUPS_BUCKET": bucket.name,
    }

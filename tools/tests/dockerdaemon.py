# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the trials that run an image share: whether a daemon answers, and where an image is pulled.

``docker`` installed is not enough: a daemon stopped, or a user outside the group docker, makes
every ``docker run`` fail, and a trial must then skip rather than fail on its fixture (#4321).
"""

import os
import shutil
import subprocess

# How the Compose files prefix the image of a third party: the registry a workstation pulls from.
MIRROR = "${WATERFALL_MIRROR:-}"


def answers() -> bool:
    """Tell whether ``docker`` is installed and its daemon answers this user."""
    if shutil.which("docker") is None:
        return False
    try:
        done = subprocess.run(
            ["docker", "info"], capture_output=True, check=False, timeout=30
        )
    except subprocess.TimeoutExpired:
        return False
    return done.returncode == 0


def mirrored(image: str) -> str:
    """Give an image of the Compose as Compose pulls it: behind ``WATERFALL_MIRROR``, if set."""
    return image.replace(MIRROR, os.environ.get("WATERFALL_MIRROR", ""))

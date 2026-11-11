"""Location of user data (database, logs, Mission Control config and caches).

Everything the application writes lives under one directory so that an
installed package never writes into ``site-packages`` or the current working
directory. Override it with the ``SATORBIT_HOME`` environment variable
(the Docker image sets it to ``/data``).
"""

from __future__ import annotations

import os
from pathlib import Path


def data_home() -> Path:
    """Return the data directory, creating it if needed."""
    home = Path(os.environ.get("SATORBIT_HOME", Path.home() / ".satorbit")).expanduser()
    home.mkdir(parents=True, exist_ok=True)
    return home

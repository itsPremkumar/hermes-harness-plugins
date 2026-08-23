'''Target module whose API must be documented by the docs-sync domain.'''


def connect(uri, timeout=30, retries=3):
    """Open a connection to the store."""


def disconnect(handle, force=False):
    """Close a connection."""


def fetch_batch(handle, keys, strict=True):
    """Fetch many keys; strict raises on any miss."""


def stream_all(handle, chunk_size=500):
    """Yield rows in chunks."""


class Pool:
    """Bounded connection pool."""

    def acquire(self, wait=True):
        """Take a connection from the pool."""

    def release(self, handle, broken=False):
        """Return a connection; broken ones are discarded."""

    def stats(self):
        """Snapshot of pool counters."""


def migrate(schema_version, dry_run=False):
    """Apply schema migrations up to schema_version."""

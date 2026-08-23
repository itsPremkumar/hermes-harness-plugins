# Store Client — API Reference

Complete documentation of the store client public API.

## connect

def connect(uri, timeout=?, retries=?):

- `uri` — address of the store
- `timeout` — seconds before the attempt fails
- `retries` — retry count

## disconnect

def disconnect(handle, force=?):

- `handle` — connection handle returned by connect
- `force` — discard pending buffers instead of flushing

## fetch_batch

def fetch_batch(handle, keys, strict=?):

- `handle` — open connection
- `keys` — iterable of keys to load
- `strict` — raise on any missing key instead of returning None entries

## stream_all

def stream_all(handle, chunk_size=?):

- `handle` — open connection
- `chunk_size` — rows yielded per chunk

## Pool

class Pool:

Bounded connection pool.

### Pool.acquire

def acquire(self, wait=?):

- `self` — pool instance
- `wait` — block until a connection is free instead of raising

### Pool.release

def release(self, handle, broken=?):

- `self` — pool instance
- `handle` — connection being returned
- `broken` — discard the connection instead of reusing it

### Pool.stats

def stats(self):

- `self` — pool instance

Snapshot of pool counters.

## migrate

def migrate(schema_version, dry_run=?):

- `schema_version` — target schema version to migrate up to
- `dry_run` — plan the migration without applying it

#!/bin/sh
set -e

# Fail fast on directory permission issues
# Root cause of most production failures: non-root user (kidney-api) can't write
# to /app/.cache or /app/data, causing silent fallbacks and 100% CPU
for dir in /app/.cache /app/data; do
  if [ ! -d "$dir" ]; then
    echo "FATAL: Required directory $dir does not exist" >&2
    exit 1
  fi
  if [ ! -w "$dir" ]; then
    echo "FATAL: Directory $dir is not writable by $(whoami) (uid=$(id -u), gid=$(id -g))" >&2
    echo "  Fix: Ensure volume ownership matches container user (uid=1000, gid=1000)" >&2
    exit 1
  fi
done

echo "Directory permissions OK (uid=$(id -u))"

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head

# Start the application
exec "$@"

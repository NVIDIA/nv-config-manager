#!/bin/bash
# Run migrations before starting Nautobot

set -e

# Run migrations automatically (only for the main nautobot service, not worker/beat)
if [[ "$1" == "nautobot-server" && "$2" == "runserver" ]]; then
    echo "Running database migrations..."
    nautobot-server migrate --no-input
fi

# Execute the original command
exec "$@"

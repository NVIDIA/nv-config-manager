#!/bin/bash
# Kea Database Admin Entrypoint
# Uses the official kea-admin tool for database initialization and upgrades.
# Reference: https://kea.readthedocs.io/en/kea-2.6.2/arm/admin.html
set -e

if [[ -z "$INI_FILE" ]]; then
  INI_FILE=/etc/vault/nv-config-manager.ini
fi

if [[ ! -f "$INI_FILE" ]]; then
  echo "Error: $INI_FILE does not exist" >&2
  exit 1
fi

# Parse database connection details from nv_config_manager.ini
export DB_HOST=$(grep -A 6 '\[dhcp.lease_db\]' $INI_FILE | grep 'host = ' | awk -F ' = ' '{print $2}' | head -n 1)
export DB_PORT=$(grep -A 6 '\[dhcp.lease_db\]' $INI_FILE | grep 'port = ' | awk -F ' = ' '{print $2}' | head -n 1)
export DB_USER=$(grep -A 6 '\[dhcp.lease_db\]' $INI_FILE | grep 'user = ' | awk -F ' = ' '{print $2}' | head -n 1)
export DB_PASSWORD=$(grep -A 6 '\[dhcp.lease_db\]' $INI_FILE | grep 'password = ' | awk -F ' = ' '{print $2}' | head -n 1)
export DB_NAME=$(grep -A 6 '\[dhcp.lease_db\]' $INI_FILE | grep 'database = ' | awk -F ' = ' '{print $2}' | head -n 1)

echo "Database configuration:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  User: $DB_USER"
echo "  Database: $DB_NAME"

# Validate required variables
if [[ -z "$DB_HOST" || -z "$DB_PORT" || -z "$DB_USER" || -z "$DB_PASSWORD" || -z "$DB_NAME" ]]; then
    echo "Error: Required database configuration not found in $INI_FILE" >&2
    echo "Please ensure [dhcp.lease_db] section has host, port, user, password, and database" >&2
    exit 1
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\q' 2>/dev/null; do
    echo "Still waiting for PostgreSQL..."
    sleep 2
done
echo "PostgreSQL is ready!"

# Check if schema already exists (idempotent check)
echo "Checking if Kea schema already exists..."
if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U "$DB_USER" -d "$DB_NAME" -c "SELECT version, minor FROM schema_version;" 2>/dev/null; then
    CURRENT_VERSION=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT version || '.' || minor FROM schema_version;" 2>/dev/null | tr -d ' ')
    echo "Kea schema already exists at version $CURRENT_VERSION"
    
    # Check if upgrade is needed
    echo "Checking if schema upgrade is needed..."
    kea-admin db-upgrade pgsql -h $DB_HOST -P $DB_PORT -u $DB_USER -p $DB_PASSWORD -n $DB_NAME || true
    
    echo "Schema check complete."
    exit 0
fi

# Initialize the database schema using kea-admin
echo "Initializing Kea DHCP database schema..."
kea-admin db-init pgsql -h $DB_HOST -P $DB_PORT -u $DB_USER -p $DB_PASSWORD -n $DB_NAME

# Verify schema was created
echo "Verifying schema version..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U "$DB_USER" -d "$DB_NAME" -c "SELECT version, minor FROM schema_version;" || {
    echo "Error: Failed to verify schema version after initialization" >&2
    exit 1
}

echo "Kea database schema initialized successfully!"

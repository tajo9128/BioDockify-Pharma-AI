#!/bin/bash

echo "Running initialization script..."

# branch from parameter
if [ -z "$1" ]; then
    echo "Error: Branch parameter is empty. Please provide a valid branch name."
    exit 1
fi
BRANCH="$1"

# Copy all contents from persistent /per to root directory (/) without overwriting
cp -r --no-preserve=ownership,mode /per/* /

# allow execution of /root/.bashrc and /root/.profile
chmod 444 /root/.bashrc
chmod 444 /root/.profile

# Install cron backup job (daily 3 AM auto-backup of all 3 data locations)
if [ -f /etc/cron.d/biodockify-backup ]; then
    chmod 644 /etc/cron.d/biodockify-backup
    chown root:root /etc/cron.d/biodockify-backup
    # cron requires /etc/cron.d permissions to be exact
    echo "[init] Auto-backup cron job installed (daily 3 AM)"
fi

# Run a startup backup in the background (non-blocking) — captures current state
# on every container restart so users always have a recent backup
if [ -x /a0/docker/run/auto_backup.sh ]; then
    (sleep 60 && /a0/docker/run/auto_backup.sh > /var/log/biodockify-startup-backup.log 2>&1) &
    echo "[init] Scheduled startup backup (60s delay)"
fi

# update package list to save time later
apt-get update > /dev/null 2>&1 &

# let supervisord handle the services
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf

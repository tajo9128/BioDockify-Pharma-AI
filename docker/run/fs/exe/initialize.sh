#!/bin/bash

echo "Running initialization script..."

# ─── Consolidate data: /a0/data and /a0/.a0proj → /a0/usr ───
# The base image has VOLUME directives that create anonymous volumes at these paths.
# We want ALL persistent data under /a0/usr (single user-facing volume).
# On first start: copy existing data into /a0/usr, then replace dirs with symlinks.
# On subsequent starts: dirs are already symlinks (from image build), but Docker
# mounts anonymous volumes on top — so we re-create symlinks every time.
if [ -d /a0/data ] && [ ! -L /a0/data ]; then
    # /a0/data is a real dir (anonymous volume) — copy contents into /a0/usr
    mkdir -p /a0/usr/data
    cp -a /a0/data/. /a0/usr/data/ 2>/dev/null
fi
if [ -d /a0/.a0proj ] && [ ! -L /a0/.a0proj ]; then
    # /a0/.a0proj is a real dir (anonymous volume) — copy contents into /a0/usr
    mkdir -p /a0/usr/.a0proj
    cp -a /a0/.a0proj/. /a0/usr/.a0proj/ 2>/dev/null
fi
# Replace with symlinks so all future writes go to /a0/usr
rm -rf /a0/data /a0/.a0proj 2>/dev/null
ln -sf /a0/usr/data /a0/data
ln -sf /a0/usr/.a0proj /a0/.a0proj
# Ensure symlink targets exist (auto_store and knowledge.py write here)
mkdir -p /a0/usr/data/knowledge_base /a0/usr/.a0proj/memory /a0/usr/.a0proj/instructions
echo "[init] Data consolidated: /a0/data → /a0/usr/data, /a0/.a0proj → /a0/usr/.a0proj"

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

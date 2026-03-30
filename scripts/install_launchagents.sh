#!/bin/bash
# install_launchagents.sh — Installe les LaunchAgents iAgent (heartbeat + telegram).
set -e
cd ~/.iagent

ACTUAL_USER=$(whoami)

echo "=== Installation LaunchAgents iAgent ==="

# Heartbeat
echo "Installation com.iagent.heartbeat..."
launchctl unload ~/Library/LaunchAgents/com.iagent.heartbeat.plist 2>/dev/null || true
sed "s/USERNAME/${ACTUAL_USER}/g" launchagents/com.iagent.heartbeat.plist > ~/Library/LaunchAgents/com.iagent.heartbeat.plist
launchctl load ~/Library/LaunchAgents/com.iagent.heartbeat.plist
echo "✓ heartbeat installé"

# Gateway Telegram
echo "Installation com.iagent.telegram..."
launchctl unload ~/Library/LaunchAgents/com.iagent.telegram.plist 2>/dev/null || true
sed "s/USERNAME/${ACTUAL_USER}/g" launchagents/com.iagent.telegram.plist > ~/Library/LaunchAgents/com.iagent.telegram.plist
launchctl load ~/Library/LaunchAgents/com.iagent.telegram.plist
echo "✓ telegram installé"

# Vérification
echo ""
echo "=== Vérification ==="
launchctl list | grep iagent || echo "Aucun agent iagent trouvé"
echo ""
echo "=== Terminé ==="

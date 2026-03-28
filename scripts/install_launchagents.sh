#!/bin/bash
# install_launchagents.sh — Installe le heartbeat iAgent uniquement.
# Le gateway Telegram sera installé lors du décommissionnement de l'ancien système.
set -e
cd ~/.iagent

echo "=== Installation LaunchAgents iAgent ==="

# Heartbeat
echo "Installation com.iagent.heartbeat..."
launchctl unload ~/Library/LaunchAgents/com.iagent.heartbeat.plist 2>/dev/null || true
cp launchagents/com.iagent.heartbeat.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.iagent.heartbeat.plist
echo "✓ heartbeat installé"

echo ""
echo "⚠️  com.iagent.telegram NON installé (démarrer lors du décommissionnement de l'ancien système)"
echo "    Commande :"
echo "    cp ~/.iagent/launchagents/com.iagent.telegram.plist ~/Library/LaunchAgents/"
echo ""

# Vérification
echo "=== Vérification ==="
launchctl list | grep iagent || echo "Aucun agent iagent trouvé"
echo ""
echo "=== Terminé ==="

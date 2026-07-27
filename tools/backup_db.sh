#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FECHA=$(date +%Y-%m-%d_%H-%M-%S)

# Crear directorio de backups si no existe
mkdir -p "$DIR/backups"

# Respaldar base de datos y archivos JSON de conocimiento en un archivo comprimido
tar -czf "$DIR/backups/amibot_backup_$FECHA.tar.gz" -C "$DIR" consultas.db conocimiento_base_ollama.json chitchat_patterns.json 2>/dev/null

echo "Backup completado: backups/amibot_backup_$FECHA.tar.gz"

# Mantener solo los últimos 5 backups (eliminar los más antiguos)
cd "$DIR/backups" || exit
ls -t amibot_backup_*.tar.gz | tail -n +6 | xargs -r rm -f --

echo "Rotación automática: Se conservan solo los 5 backups más recientes."

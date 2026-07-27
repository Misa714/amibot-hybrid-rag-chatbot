#!/bin/bash
echo "🛑 Deteniendo servidores anteriores..."
PID=$(lsof -ti :8000)
if [ ! -z "$PID" ]; then
    kill -9 $PID
    echo "✅ Proceso $PID detenido"
fi
source venv/bin/activate
echo "🚀 Iniciando servidor..."
python3 main.py

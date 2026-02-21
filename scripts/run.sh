#!/bin/bash
# Скрипт запуска из любой директории
if [[ $PATH != *"$HOME/Desktop/Work/vNE/CEE/scripts"* ]]; then
	echo "Чтобы запускать run.sh из любой директории, добавьте в ~/.bashrc:"
	echo 'export PATH="$HOME/Desktop/Work/vNE/CEE/scripts:$PATH"'
	echo "и выполните: source ~/.bashrc"
	echo "После этого можно запускать run.sh из любой папки."
	echo
fi
SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)"

# Добавить scripts/ в PATH для текущей сессии
export PATH="$SCRIPT_PATH:$PATH"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CLIENT_SCRIPT="$PROJECT_ROOT/cee-lcm/scripts/interactive_auth_demo.py"

if [ ! -f "$CLIENT_SCRIPT" ]; then
	echo "❌ Не найден $CLIENT_SCRIPT"
	exit 1
fi

python3 "$CLIENT_SCRIPT"

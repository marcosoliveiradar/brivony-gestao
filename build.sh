#!/usr/bin/env bash
# Script de build usado pelo Render a cada publicação.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Cria o usuário de acesso ou atualiza a senha dele a partir das variáveis do painel.
python manage.py garantir_usuario

# Dados fictícios de demonstração (desligue com DEMO_DATA=False).
if [[ "${DEMO_DATA:-False}" == "True" ]]; then
  python manage.py popular_demo
fi

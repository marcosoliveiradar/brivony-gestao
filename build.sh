#!/usr/bin/env bash
# Script de build usado pelo Render a cada publicação.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Cria o usuário de acesso só se as variáveis existirem e ele ainda não existir.
if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  python manage.py createsuperuser --noinput --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.invalid}" \
    || echo "Usuário ${DJANGO_SUPERUSER_USERNAME} já existe; mantido."
fi

# Dados fictícios de demonstração (desligue com DEMO_DATA=False).
if [[ "${DEMO_DATA:-False}" == "True" ]]; then
  python manage.py popular_demo
fi

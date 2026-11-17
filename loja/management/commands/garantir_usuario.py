"""Cria ou atualiza o usuário de acesso a partir de variáveis de ambiente.

Usado no build do Render: se DJANGO_SUPERUSER_PASSWORD mudar no painel,
a senha do usuário existente também é atualizada na próxima publicação.
A senha passa pelos validadores do Django e é guardada com PBKDF2.
"""
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria ou atualiza o usuário de acesso com DJANGO_SUPERUSER_USERNAME e DJANGO_SUPERUSER_PASSWORD."

    def handle(self, *args, **options):
        usuario = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        senha = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not usuario or not senha:
            self.stdout.write("Variáveis do usuário de acesso não definidas; nada a fazer.")
            return

        User = get_user_model()
        user, criado = User.objects.get_or_create(
            username=usuario,
            defaults={"email": os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.invalid")},
        )
        try:
            validate_password(senha, user)
        except ValidationError as erro:
            # Não derruba a publicação: mantém a senha atual e avisa no log do Render.
            self.stderr.write(
                "AVISO: senha recusada por ser fraca (" + " ".join(erro.messages) + "). "
                "A senha anterior foi mantida. Use uma senha mais forte."
            )
            if criado:
                user.set_unusable_password()
                user.save()
            return

        if not user.check_password(senha):
            user.set_password(senha)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Usuário {usuario} {'criado' if criado else 'atualizado'}."))

"""Testes de fumaça da configuração do projeto."""
from django.conf import settings
from django.test import TestCase


class ConfiguracaoTests(TestCase):
    def test_senhas_usam_pbkdf2(self):
        self.assertEqual(
            settings.PASSWORD_HASHERS[0], "django.contrib.auth.hashers.PBKDF2PasswordHasher"
        )

    def test_admin_exige_login(self):
        resposta = self.client.get("/admin/")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/admin/login/", resposta.url)

    def test_idioma_e_fuso(self):
        self.assertEqual(settings.LANGUAGE_CODE, "pt-br")
        self.assertEqual(settings.TIME_ZONE, "America/Sao_Paulo")

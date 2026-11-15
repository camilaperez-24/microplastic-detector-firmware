"""
secrets_ejemplo.py — Plantilla de firmware/secrets.py
=====================================================

Cómo usarlo:
1. Copiar este archivo como firmware/secrets.py (mismo lugar, otro nombre).
2. Cambiar la contraseña por una propia, de mínimo 8 caracteres.
3. Subir firmware/secrets.py a la Pico junto con el resto de firmware/.

firmware/secrets.py NO se sube a GitHub (está en .gitignore), así la
contraseña real no queda publicada en el repositorio.

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

WIFI_AP_PASSWORD = "cambiar-esta-clave"
"""Contraseña de la red Detector-PE (mínimo 8 caracteres)."""

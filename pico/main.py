"""
main.py — Arranque automático en la Pico
=========================================

Este archivo va en la RAÍZ de la Pico (/main.py), no dentro de firmware/.
MicroPython lo ejecuta solo cada vez que la Pico recibe corriente, así
el firmware arranca sin computador (por ejemplo, con un cargador de celular).

Para usar Thonny como siempre: conectar la Pico y presionar Stop (o Ctrl+C);
el firmware se detiene y queda la consola libre.
Para quitar el arranque automático: borrar o renombrar /main.py en la Pico.

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

from firmware.main import main

main()

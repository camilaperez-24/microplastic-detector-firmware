# Microplastic Detector Firmware

Firmware de adquisición y procesamiento para el prototipo optoelectrónico
de detección preliminar de partículas compatibles con microplásticos tipo
polietileno en muestras de agua.

**Proyecto de Grado II — Ingeniería Electrónica**
Universidad Santo Tomás · Bogotá · 2026-2

---

## Autores

- Camila Pérez Mercado — Cód. 2353969
- Diego Alejandro Rodríguez Guzmán — Cód. 2366603

## Director

- M.Sc. Oscar Mauricio Gelvez Lizarazo

## Codirector

- M.Sc. Carlos Javier Mojica Casallas

Grupo de Investigación MEM · Facultad de Ingeniería Electrónica

---

## Descripción

Este repositorio contiene el firmware que corre en una **Raspberry Pi Pico 2 W**
y gobierna el prototipo de medición óptica. Sus responsabilidades son:

1. Controlar un LED infrarrojo de iluminación.
2. Adquirir la señal del fotodetector (OPT101) a través del ADC.
3. Calcular estadística por medición (media, desviación estándar, ΔV).
4. Entregar los resultados por USB serial y, opcionalmente, por WiFi.

El sistema no identifica químicamente el polímero: estima la **presencia
probable** de partículas en suspensión mediante análisis de variaciones de
intensidad óptica.

## Hardware

- Raspberry Pi Pico 2 W (RP2350)
- Fotodetector OPT101 (transimpedancia integrada)
- LED infrarrojo + resistencia limitadora de 56 Ω
- Cámara óptica cerrada con microcanal en L
- Alimentación: USB (5 V → regulador interno 3.3 V)

## Estructura del proyecto
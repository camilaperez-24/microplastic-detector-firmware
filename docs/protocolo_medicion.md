# Protocolo de medición

Versión del 14-oct-2026. Si se cambia algo del procedimiento, anotarlo aquí con la fecha.

## 1. Preparación (una vez por sesión)

1. Escribir en el cuaderno: fecha, lugar, **regla de descarte** (sección 3),
   lote del agua y descripción de la muestra de PE (número, tamaño, origen, color).
2. Montaje: tubo en su posición marcada en la mesa, con el tope abajo y el ángulo fijo.
   **Tapar el extremo superior del tubo o cubrir el montaje con una caja o tela oscura**.
3. Chip marcado en el borde: qué extremo entra primero, qué cara va hacia el LED
   y dónde queda la zona frente al sensor.
4. Materiales separados y marcados: vasito y pipeta o jeringa **solo para agua limpia**,
   y otros **solo para PE**. Pipetas nuevas, enjuagadas con agua estéril.
5. Agua estéril a temperatura ambiente (unos 30 min fuera antes de medir).

## 2. Verificación inicial (obligatoria, antes del primer MEASURE)

1. En Thonny, arrancar el firmware y esperar `# listo`.
2. Con agua limpia en el chip, `MONITOR 20`. Debe dar:
   - `mu_dark` ≈ 15–40 cuentas (si es mucho mayor, entra luz o hay un cable suelto)
   - `mu_light` entre 600 y 2500, y menor que 3050
   - `sigma_light` ≈ 15–25
3. Con la cámara del celular, comprobar que **el LED parpadea** (1 s apagado, 1 s encendido).

Si algo no cumple, **no medir**: revisar conexiones (pin 5 del OPT101 → GP26; LED y transistor).

## 3. Regla de descarte (definida antes de medir)

1. Antes de meter el chip, mirarlo a contraluz. Si hay una **burbuja** en la zona del
   sensor, vaciar y volver a llenar. Si después de 3 intentos sigue, anotar
   "descartado: burbuja" y pasar al siguiente.
2. Una vez escrito `MEASURE`, **el llenado cuenta**, dé el número que dé.
3. Solo se descarta después si el firmware marca `SATURADO` o `ERROR`, o si hubo una
   falla física **anotada en el momento** (cable suelto, se movió el tubo, golpe a la mesa).
4. **Nunca** descartar un llenado porque el número "salió raro".
5. Los datos descartados no se borran: se dejan en la evidencia con la anotación.

## 4. Ciclo de un llenado

1. Sacar el chip tomándolo por los bordes y vaciarlo.
2. Llenar despacio, siempre con el mismo volumen y el mismo método.
   - Agua limpia: jeringa o pipeta de agua limpia.
   - PE: aspirar las partículas con su pipeta y soltarlas despacio,
     **sin apretar hasta el final** (eso mete aire). Completar con agua limpia si hace falta.
3. Revisar a contraluz: burbujas (aplicar la regla) y, en PE, contar las partículas
   y anotar cuántas quedaron en la zona del sensor. **Foto a contraluz.**
4. Secar las caras externas con papel sin pelusa.
5. Meter el chip con la orientación marcada hasta el tope; tubo en su posición; tapar.
6. `SET ID=...` (sin espacios alrededor del `=`), revisar la respuesta `# OK ... ID=...`,
   y luego `MEASURE`.
7. No tocar nada hasta `# FIN`.
8. En PE: antes de sacar el chip, **segunda foto** (el PE flota y puede moverse).
   Vaciar en un recipiente limpio, **contar las partículas** y enjuagar el chip
   2–3 veces con agua limpia, revisando que no quede ninguna.

## 5. Orden de las muestras

Alternar siempre: `pe_01`, `limpia_01`, `pe_02`, `limpia_02`, `pe_03`, `limpia_03`
(o empezando por limpia). Alternar evita que una deriva lenta favorezca a un grupo.
Si una partícula queda atrapada y no sale del chip, no alternar: medir primero todos
los de agua limpia y luego los de PE, y anotarlo.

## 6. Tabla de notas por llenado

| # | ID | ¿Burbujas? | Partículas en el chip | Partículas en la zona del sensor | Fotos | Observaciones |
|---|---|---|---|---|---|---|

## 7. Al terminar

1. Copiar toda la salida de la Shell a `evidencias/<prueba>_<fecha>.txt`, con las notas al final.
2. `git add`, `git commit`, `git push`.
3. Actualizar `docs/estado_del_proyecto.md`.

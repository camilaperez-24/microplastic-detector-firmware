# Protocolo de medición

Versión del 14-oct-2026, rev. 2 (control de burbujas, después del piloto del 14-oct).
Si se cambia algo del procedimiento, anotarlo aquí con la fecha.

## 1. Preparación (una vez por sesión)

1. Escribir en el cuaderno: fecha, lugar, **regla de descarte** (sección 3),
   lote del agua y descripción de la muestra de PE (número, tamaño, origen, color).
2. Montaje: tubo en su posición marcada en la mesa, con el tope abajo y el ángulo fijo.
   **Tapar el extremo superior del tubo o cubrir el montaje con una caja o tela oscura**.
3. Chip marcado en el borde: qué extremo entra primero, qué cara va hacia el LED
   y dónde queda la zona frente al sensor.
4. Materiales separados y marcados: vasito y pipeta o jeringa **solo para agua limpia**,
   y otros **solo para PE**. Pipetas nuevas, enjuagadas con agua estéril.
5. Agua estéril a temperatura ambiente (unos 30 min fuera antes de medir), servida
   despacio en su vasito y **sin agitar**: el agua fría o agitada suelta burbujas.
6. Partículas de PE en remojo en agua limpia al menos 10 min antes, moviendo el vasito
   con suavidad: el PE repele el agua y suele llevar aire pegado.

## 2. Verificación inicial (obligatoria, antes del primer MEASURE)

1. En Thonny, arrancar el firmware y esperar `# listo`.
2. Con agua limpia en el chip, `MONITOR 20`. Debe dar:
   - `mu_dark` ≈ 15–40 cuentas (si es mucho mayor, entra luz o hay un cable suelto)
   - `mu_light` entre 600 y 2500, y menor que 3050
   - `sigma_light` ≈ 15–25
3. Con la cámara del celular, comprobar que **el LED parpadea** (1 s apagado, 1 s encendido).
4. Anotar el ΔV de esta verificación: es la referencia de la sesión.

Si algo no cumple, **no medir**: revisar conexiones (pin 5 del OPT101 → GP26; LED y transistor).
Si `mu_light` sale muy bajo y las conexiones están bien, sacar el chip y repetir el `MONITOR`:
si sin chip sigue bajo, el sensor no está de frente al LED → alinear (sección 8).

## 3. Regla de descarte (definida antes de medir)

1. Antes de meter el chip, mirar a contraluz la zona del sensor. Si hay una **burbuja**,
   vaciar y volver a llenar **de inmediato; no esperar a que se vaya sola**.
   Si después de 3 intentos sigue, anotar "descartado: burbuja" y pasar al siguiente.
2. Una vez escrito `MEASURE`, **el llenado cuenta**, dé el número que dé.
3. Solo se descarta después si el firmware marca `SATURADO` o `ERROR`, o si hubo una
   falla física **anotada en el momento** (cable suelto, se movió el tubo, golpe a la mesa).
4. **Nunca** descartar un llenado porque el número "salió raro".
5. Los datos descartados no se borran: se dejan en la evidencia con la anotación.
6. **Burbuja al sacar** (paso 8 del ciclo): no descarta el llenado. Se anota, y el análisis
   se hace dos veces: el principal con todos los llenados y uno secundario sin los que
   tenían burbuja al sacar. Se reportan los dos. La regla es igual para limpia y PE.

## 4. Ciclo de un llenado

1. Sacar el chip tomándolo por los bordes y vaciarlo.
2. Llenar despacio, siempre con el mismo volumen y el mismo método:
   - Purgar la jeringa o pipeta: punta hacia arriba, empujar hasta que salga una gota.
   - Chip inclinado; llenar por el extremo más bajo para que el aire salga por el más alto.
   - **No apretar hasta el final** (eso mete aire).
   - Agua limpia: jeringa o pipeta de agua limpia.
   - PE: aspirar las partículas ya remojadas con su pipeta y soltarlas despacio.
     Completar con agua limpia si hace falta.
3. Dar golpecitos suaves al chip y revisar a contraluz la zona del sensor (regla 1 de la
   sección 3). En PE, contar las partículas y anotar cuántas quedaron en la zona del sensor.
   **Foto a contraluz.**
4. Secar las caras externas con papel sin pelusa.
5. Meter el chip con la orientación marcada hasta el tope; tubo en su posición; tapar.
6. `SET ID=...` (sin espacios alrededor del `=`), revisar la respuesta `# OK ... ID=...`,
   y luego `MEASURE`.
7. No tocar nada hasta `# FIN`.
8. **En todos los llenados:** sacar el chip despacio y sin voltearlo, mirar de inmediato la
   zona del sensor a contraluz y tomar la **segunda foto**. Anotar si hay burbuja (regla 6).
9. Vaciar en un recipiente limpio. En PE: **contar las partículas** y enjuagar el chip
   2–3 veces con agua limpia, revisando que no quede ninguna.

## 5. Orden de las muestras

Alternar siempre: `pe_01`, `limpia_01`, `pe_02`, `limpia_02`, `pe_03`, `limpia_03`
(o empezando por limpia). Alternar evita que una deriva lenta favorezca a un grupo.
El 14-oct las partículas salieron del chip en todos los llenados, así que se mantiene la alternancia.
Si alguna vez una partícula queda atrapada y no sale, no alternar: medir primero todos
los de agua limpia y luego los de PE, y anotarlo.

## 6. Tabla de notas por llenado

| # | ID | Burbujas antes (intentos) | Partículas en el chip | Partículas en la zona del sensor | Burbuja al sacar | Partículas recuperadas | Fotos | Observaciones |
|---|---|---|---|---|---|---|---|---|

## 7. Al terminar

1. **MONITOR de cierre:** lavar el chip, llenarlo con agua limpia y hacer `MONITOR 20`.
   ΔV debe quedar dentro de ~4 % de la verificación inicial. Si no, anotarlo.
2. Copiar toda la salida de la Shell a `evidencias/<prueba>_<fecha>.txt`, con las notas al final.
3. `git add`, `git commit`, `git push`.
4. Actualizar `docs/estado_del_proyecto.md`.

## 8. Alineación del sensor (solo si se movió el OPT101 o el LED)

Agregada el 18-oct-2026.

1. Chip con agua limpia, sin burbujas, metido hasta el tope.
2. `MONITOR 120` (repetir si se acaba). Mirar el **quinto valor, `dV`**, no `mu_light`:
   `dV` ya resta la luz del cuarto que entra con el tubo abierto.
3. Mover el OPT101 medio milímetro en una sola dirección. **Ignorar la primera línea**
   después de moverlo (mezcla las dos posiciones) y leer la segunda.
4. Si `dV` sube, seguir en esa dirección; si baja, volver y probar la contraria.
   Cuando empiece a bajar, se pasó el máximo: regresar al punto más alto.
5. Repetir en la otra dirección (arriba/abajo) y, si se puede, en el ángulo.
6. Si `dV` está en unas decenas y casi no cambia, el sensor está lejos del haz y solo
   le llegan reflejos: ponerlo de frente al LED a ojo y volver a empezar.
7. `mu_light` debe quedar **por debajo de 3050** (ideal ΔV 2000–2500 con agua). Si satura
   en el máximo, la solución definitiva es subir R_LED, no correr el sensor.
8. Fijar el sensor sin empujarlo, tapar y confirmar con `MONITOR 20`. Marcar la posición
   en el tubo, tomar foto y anotar el ΔV final como referencia.

## 9. Medir desde el celular (firmware 0.2.1, opcional)

Agregada el 5-nov-2026. El protocolo es el mismo; solo cambia dónde se escriben los comandos.
Configuración inicial y detalles: `README.md` (sección "Medir desde el celular") y `docs/plan_wifi.md`.
**Antes de usarlo para datos de la tesis, hacer la prueba de validación** (`docs/plan_wifi.md`, sección 7).

| Paso del protocolo | En Thonny | En la página (http://192.168.4.1) |
|---|---|---|
| Verificación inicial y cierre (secciones 2 y 7) | `MONITOR 20` | **Monitor 20 s** |
| Referencia de la sesión | ΔV del `MONITOR` inicial | **Tomar referencia** (`BASELINE` con agua limpia, ID `ref`) |
| Cada llenado (sección 4, paso 6) | `SET ID=...` y `MEASURE` | Escribir el ID (o tocar la sugerencia) y **Medir este llenado** |
| Cancelar | `STOP` | **Detener** |
| Guardar la salida (sección 7, paso 2) | Copiar la Shell | **Descargar CSV de la sesión** (copia también en la Pico, `/datos/`) |

- La página clasifica cada llenado con la regla de la campaña: *T*<sub>rel</sub> = ΔV / ΔV<sub>ref</sub>;
  menos de 80 % es *PE probable*. Si el firmware marca `SATURADO` o `ERROR`, la página lo muestra
  como *No válido* (regla de descarte, sección 3).
- La página se actualiza cada ~2 s mientras se mide (la Pico la atiende entre repeticiones).
- Si el celular se desconecta, la medición sigue y los datos quedan en la Pico.

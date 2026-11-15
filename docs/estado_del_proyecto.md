# Estado del proyecto — resultados, decisiones y pendientes

Actualizado: 5-nov-2026. Agregar una entrada nueva cada vez que haya una prueba o decisión importante.

## Cronología

| Fecha | Qué se hizo | Resultado clave | Evidencia |
|---|---|---|---|
| 09-oct | Repositorio, `config.py`, `stats.py` (21 tests), `record.py` (23 tests) | Núcleo estadístico validado en PC | commits iniciales |
| 10-oct | MicroPython en la Pico; prueba del ADC con GND y 3V3; `adq.py` | ADC sano; Fs real 1000.0 Hz, 0 muestras atrasadas | capturas |
| 10-oct | Paso del circuito de 5 V con divisor a 3.3 V directo; LED con 2N2222 | OPT101 saturaba con 56 Ω; se aumentó R_LED | — |
| 11-oct | Prueba de estabilidad (5 min) | Deriva exponencial, τ ≈ 69 s → calentamiento de 180 s | `evidencias/estabilidad_2026-10-11.md` |
| 11-oct | Firmware v0.2.0 completo (`io_serial`, `main`), 83 tests | Validado en la Pico | commit `88f7d5b` |
| 11-oct | Reproducibilidad sin rellenar (3 MEASURE) | ΔV 1818.0 / 1817.5 / 1816.3 → 0.05 % | `evidencias/reproducibilidad_2026-10-11.txt` |
| 12-oct | 5 llenados con agua estéril, sacando el chip | Variación entre llenados ~4 %; un atípico de −40 % | `evidencias/llenados_2026-10-12.txt` |
| 13-oct | Piloto con PE, primer intento (`pe_01`, R001) | **Inválido**: el LED no funcionaba (ΔV = 8) | `evidencias/piloto_pe_2026-10-13.txt` |
| 14-oct | Piloto con PE: 6 llenados alternados, tubo tapado | Instrumento estable, pero el agua limpia dio 2072 / 1105 / 74 → **inconcluso** (Welch p = 0.30). Causa más probable: burbujas | `evidencias/piloto_pe_2026-10-14.txt` |
| 17/18-oct | Reubicación y alineación del OPT101 | En la primera posición nueva el sensor quedó fuera del haz (ΔV ≈ 60 con chip, 44 sin chip). Se alineó con `MONITOR` buscando el máximo de ΔV (sin chip llegó a saturar, ~3130). Posición final fijada: **ΔV ≈ 2221** con agua limpia, σ 1.1 %, sin saturar | `evidencias/alineacion_sensor_2026-10-17.txt` |
| 18-oct | Piloto con PE repetido (protocolo rev. 2): 6 llenados alternados, 2 partículas por llenado de PE | Limpias 2212 / 2216 / 2120 (CV 2.5 %); PE 841 / 1039 / 592 (−62 % en promedio). **Welch t = 10.2, p = 0.006**. Matriz de confusión 6 de 6 con el umbral de 80 %. Sin burbujas | `evidencias/piloto_pe_2026-10-18.txt` |
| 20-oct | Campaña con el chip 2: 5 limpias + 5 PE (referencia 2002; cierre +0.23 %) | Limpias 94–101 %; PE 13–55 %; p ≈ 5 × 10⁻⁴; 10 de 10. Dos llenados descartados (chip con fuga). **Campaña completa 11 + 11: p ≈ 2 × 10⁻⁸, 22 de 22** | `evidencias/campana_chip2_2026-10-20.txt` |
| 05-nov | Firmware 0.2.1: WiFi propio y página web para medir desde el celular (`session.py`, `io_wifi.py`, `web/index.html`, arranque automático). 140 tests | Probado en el PC con la Pico simulada: referencia, PE (30 %, *PE probable*), limpia (97 %), STOP, monitor y descarga del CSV. **Falta validarlo en el hardware**; `WIFI_ENABLED = False` hasta entonces | `docs/plan_wifi.md` |
| 12/13-nov | Prototipo final en baquelita: la Pico se colgaba y el LED quedó con lógica invertida y señal muy ruidosa (`sigma_light` ~1000) | Error de cableado en el bloque del LED; se volvió a soldar copiando la protoboard. `adq.py` lee la lógica del LED de `config.LED_ACTIVE_LOW` (False = como siempre) | — |
| 14-nov | Verificación del prototipo final: referencia + 2 limpias + 3 PE (chip 2) | Variación entre repeticiones 0.03 %. Limpias 100.7 / 100.4 %; PE 56.7 / 20.2 / 46.8 %: **5 de 5**. `limpia_final1` sin salida guardada (no entra). Cierre −3.9 % | `evidencias/prototipo_final_2026-11-14.txt` |
| 18-oct (tarde) | Campaña con el mismo chip: 3 limpias + 4 PE (referencia 2179) | Limpias 2235 / 2226 / 2259; PE 482 / 600 / 1235; pe_7 (581) **descartado**: el chip se filtró durante la medición. Fin del chip 1 (cedió el pegamento) | `evidencias/campana_2026-10-18_tarde.txt` |

## Caracterización del instrumento

| Magnitud | Valor |
|---|---|
| Ruido del ADC (entrada a GND) | σ ≈ 2.1 cuentas (1.7 mV) |
| Fondo con LED apagado (`mu_dark`) | ≈ 22–24 cuentas con el tubo tapado (38 sin tapar, 13-oct) |
| Ruido por lectura con LED (`sigma_light`) | ≈ 1.07 % de la señal → viene del LED/alimentación, no del ADC |
| Piso de ruido por lectura | ≈ 4.3 cuentas (igual a `sigma_dark`); con señales bajas pesa más que el 1 % del LED |
| Transmitancia del microcanal (multímetro) | vacío 88.8 %; con agua 95.0 % |
| ΔV con agua limpia | 1700–1850 cuentas el 12-oct; ≈ 2072 el 14-oct (después de reparar el LED); ≈ 2221 el 18-oct (después de alinear el sensor). **Cambia entre sesiones: cada sesión necesita su propia referencia de agua limpia** |
| Margen hasta saturar (18-oct) | `mu_light` ≈ 2243 con chip y agua, unas 800 cuentas por debajo del umbral de 3050 |
| Saturación del OPT101 a 3.3 V | ≈ 2.52 V ≈ 3128 cuentas |
| R_LED | 470 Ω → I_LED ≈ 4.3 mA calculada (V_F ≈ 1.2 V, V_CE(sat) ≈ 0.1 V); I_B ≈ 2.6 mA |

## Las tres escalas de variación (hallazgo central)

| Escala | Tamaño | Causa |
|---|---|---|
| Dentro de un bloque de 1000 muestras | ~20 cuentas | Ruido de cada lectura |
| Entre repeticiones del mismo llenado | ~0.7 cuentas (0.05 %) | Estabilidad del instrumento |
| **Entre llenados distintos** | **~70 cuentas (~4 %)**, con atípicos de −40 % a −96 % | **Procedimiento de llenado**: posición, burbujas, gotas, cómo queda el agua en la L |

Consecuencia: el límite del sistema no es la electrónica sino el llenado.

**Burbujas:** en 3 de 8 llenados de agua limpia (12 y 14-oct) hubo caídas grandes
(−40 %, −47 % y −96 %), del mismo tamaño que las que produce el PE. Por la sola
transmisión, una burbuja en el haz no se distingue de una partícula. Hoy es el
principal problema del método.

Datos de los 5 llenados del 12-oct (ΔV de la fila SUMMARY): 1689.5 / 1829.0 / 1801.8 / 1841.5 / 1098.7.
Con unos 10 llenados por grupo y σ ≈ 70 cuentas, la diferencia mínima detectable es de ~5 %.

## Piloto con PE del 14-oct

| Orden | Muestra | ΔV (SUMMARY) | Frente a limpia_01 | Calidad |
|---|---|---|---|---|
| 1 | limpia_01 | 2072.5 | — | OK |
| 2 | pe_01 | 194.3 | −90.6 % | OK |
| 3 | limpia_02 | 1104.9 | −46.7 % | OK |
| 4 | pe_02 | 230.7 | −88.9 % | OK |
| 5 | limpia_03 | 74.0 | −96.4 % | RUIDO_ALTO |
| 6 | pe_03 | 462.1 | −77.7 % | OK |

- Instrumento: `mu_dark` estable (22.2–22.7) en toda la sesión; cada llenado muy
  estable por dentro (`sem_dV` 0.07–0.34); sin saturación.
- En los tres llenados de PE entraron y salieron las 3 partículas: **no quedaron atrapadas**.
  Al final, con el chip lavado, `MONITOR` dio valores normales.
- Se vieron burbujas en dos llenados de agua limpia. Parecían desaparecer antes de medir,
  pero la señal se mantuvo baja y constante durante toda la medición (~3.5 min):
  lo que tapaba el haz siguió ahí.
- Welch con un ΔV por llenado: limpia 1083.8 ± 999, PE 295.7 ± 145; t = 1.35, p = 0.30.
  **Inconcluso**: el grupo limpio no sirve como referencia.
- Indicio sin valor estadístico: frente a limpia_01, el PE bajó ΔV entre 78 % y 91 %,
  unas 20 veces la variación normal entre llenados.
- `limpia_03` marcó `RUIDO_ALTO` por señal baja (piso de ruido de ~4.3 cuentas); no se descarta.
- Según la regla de descarte, los 6 llenados cuentan.
- Hipótesis por confirmar: el PE repele el agua y puede llevar aire pegado, así que parte
  de la caída en los llenados de PE podría venir de burbujas.

## Piloto con PE del 18-oct (protocolo rev. 2)

Referencia de la sesión (`MONITOR` inicial): ΔV ≈ 2221. Umbral: PE detectado si ΔV < 1777 (80 %).

| Orden | Muestra | ΔV (SUMMARY) | Frente a la referencia | Clasificación |
|---|---|---|---|---|
| 1 | limpia_01 | 2212.1 | 99.6 % | Limpia ✔ |
| 2 | pe_01 | 841.5 | 37.9 % | PE detectado ✔ |
| 3 | limpia_02 | 2215.8 | 99.8 % | Limpia ✔ |
| 4 | pe_02 | 1038.8 | 46.8 % | PE detectado ✔ |
| 5 | limpia_03 | 2119.8 | 95.4 % | Limpia ✔ |
| 6 | pe_03 | 591.7 | 26.6 % | PE detectado ✔ |

- Limpia: media 2182.5, desviación 54 (CV 2.5 %). PE: media 824.0, desviación 224 (CV 27 %).
- Welch: t = 10.2, gl ≈ 2.2, **p = 0.006**. IC 95 % de la diferencia: 840 a 1877 cuentas.
- Comparado con el 14-oct (p = 0.30): el cambio fue el control de burbujas; las limpias
  pasaron de variar 92 % a 2.5 %.
- Notas de Camila: no hubo burbujas en ningún llenado; se recuperaron las 2 partículas en
  los tres llenados de PE; hay fotos de todas las muestras (las sube al repositorio).
  Orientación: una acostada y una de pie en un llenado, las dos de pie en otro;
  **por confirmar con las fotos**.
- `limpia_02`: el primer reporte del calentamiento dio 2108.8 y desde el minuto 1 quedó
  estable en ~2216 (algo se acomodó al inicio; lo guardado ya estaba estable).
- No hubo `MONITOR` de cierre (se desconectó antes); `limpia_03` sirve como comprobación indirecta.
- Limitación: solo 3 llenados por grupo, partículas oscuras ubicadas a mano (mejor caso).
- Los 6 llenados cuentan para la campaña (mismo protocolo y misma alineación).

## Campaña con el chip 1 (18-oct, madrugada + tarde)

Cada llenado se expresa como % de la referencia de su sesión (madrugada 2221, tarde 2179).

| Grupo | Llenados | ΔV frente a la referencia | ΔV crudo |
|---|---|---|---|
| Limpia | 6 (limpia_01–03, limpia_4–6) | 100.5 % ± 3.0 | 2211 ± 48 |
| PE (2 partículas) | 6 (pe_01–03, pe_4–6) | 36.3 % ± 13.4 | 798 ± 294 |

- **Welch: t = 11.5, gl ≈ 5.5, p ≈ 5 × 10⁻⁵.** IC 95 % de la diferencia: 50 a 78 puntos
  porcentuales. Caída media del PE: **64 %**.
- **Matriz de confusión: 12 de 12** (6 VP, 6 VN, 0 FP, 0 FN). La limpia más baja quedó en
  95.4 % (15 puntos sobre el umbral) y el PE más alto en 56.7 % (23 puntos bajo el umbral).
- Análisis de sensibilidad incluyendo pe_7 (descartado): p ≈ 5 × 10⁻⁶, 13 de 13. No cambia la conclusión.
- `MEASURE` cancelados con `STOP` en la tarde (R001 del primer arranque, R004, R006, R007):
  chip no puesto o no metido hasta el tope, notado en el momento; se repitió el llenado.
- La campaña con este chip se cerró en 6 + 6 por una falla física (filtración), no por los datos.
- Ruido del fondo un poco mayor en la tarde (`sigma_dark` ≈ 5.5 contra 4.6 en la madrugada),
  probablemente por la luz del día; no afecta ΔV.

## Campaña con el chip 2 (20-oct)

- Referencia 2001.7; `MONITOR` de cierre 2006.4 (+0.23 %): instrumento estable en la sesión.
- Limpias: 99.5 / 94.1 / 93.7 / 100.6 / 101.0 %. PE: 26.7 / 55.0 / 20.5 / 16.1 / 12.6 %.
- Welch (chip 2): t = 9.3, gl ≈ 4.4, p ≈ 5 × 10⁻⁴. 10 de 10 bien clasificados.
- Descartados: R002 (`limpia_8`) y R007 (`limpia_9`), hechos con un chip que se filtraba.
  Cancelados con `STOP`: R001, R003, R004, R009, R016 (motivo por confirmar).
- Entró luz ambiente en parte de la sesión (`mu_dark` de 22 a 62); las limpias medidas así
  quedaron en 100.6 % y 101.0 %: la resta del fondo funciona.

## RESULTADO PRINCIPAL — campaña completa (chip 1 + chip 2)

| Grupo | n | ΔV frente a la referencia de su sesión |
|---|---|---|
| Agua limpia | 11 | 99.3 % ± 3.4 (rango 93.7–103.7 %) |
| Agua con PE (2 partículas) | 11 | 31.7 % ± 15.2 (rango 12.6–56.7 %) |

- **Welch: t = 14.4, gl ≈ 11, p ≈ 1.8 × 10⁻⁸.** Mann-Whitney: p ≈ 8.2 × 10⁻⁵.
  Caída media del PE: **68 %** (IC 95 % de la diferencia: 57 a 78 puntos).
- **Matriz de confusión: 22 de 22** (11 VP, 11 VN, 0 FP, 0 FN). Sensibilidad y
  especificidad 100 % (IC 95 % exacto: 71.5–100 %); exactitud IC 95 %: 84.6–100 %.
- Se cumple el criterio de aceptación "diferencia estadísticamente significativa" del anteproyecto.
- Bloques de LaTeX (Metodología y Resultados) y figuras: `resultados/` (entregados el 20-oct).
- Fotos a contraluz recibidas (24 + cierre); índice en `evidencias/fotos/indice_fotos.md`.
  Todas las de PE muestran una partícula en la esquina de la L; ninguna limpia muestra
  partículas ni burbujas ahí. Los dos PE con menor caída (pe_6, pe_9) tienen la partícula
  acostada. En cada foto se ve una sola mancha: las dos partículas solían quedar juntas.
  `limpia_7`: hay foto, pero la salida no se guardó; no entra al análisis.

## Prueba complementaria: una sola partícula (22-oct)

Referencia 1760.4 (umbral 1408); cierre 1774.1 (+0.78 %).

| Llenado | ΔV | T_rel | Resultado |
|---|---|---|---|
| PE_1-1particula | 483.2 | 27.4 % | Detectado |
| PE_2-1particula | 1835.0 | 104.2 % | **No detectado** |
| PE_3-1particula | 1116.1 | 63.4 % | Detectado |
| PE_4-1mmx1mm (partícula de 1 × 1 mm, exploratorio) | 1797.3 | 102.1 % | **No detectado** |

- Con una partícula: 2 de 3 detectadas. Cuando se detecta, la caída es del mismo orden que
  con dos partículas (27 % y 63 %, frente a 12.6–56.7 % en la campaña).
- PE_2 dio lo mismo que agua limpia: lo más probable es que la partícula no estuviera en el
  haz (la misma partícula dio 27 % en PE_1). Confirmado con la foto (28-oct): estaba de canto y corrida de la esquina.
- La de 1 × 1 mm no se detectó en el único llenado. Solo hay foto de esa partícula junto a la regla, no dentro del chip; no se puede confirmar si
  estaba en la zona de medición; si lo estaba, sugiere un límite inferior de tamaño.
- R003 (primer intento de PE_3) cancelado con `STOP` a los 31 s con dV = 1700.6 (96.6 %):
  la partícula se había movido fuera de la zona, notado en el momento; se reubicó y se repitió.
- Interpretación: la detección depende de que la partícula quede en la zona del haz; esto
  motiva las L (topes) como mejora y va en Limitaciones.
- Chip 2. Partícula de PE_1 a PE_3: 3 mm × 2 mm (la misma en los tres).
- Fotos: lo que cuenta es el área de la sombra que la partícula proyecta sobre el haz. Vista
  de frente (compacta) bloquea mucho; vista de canto (línea delgada) casi nada. Explica la
  variabilidad del PE en la campaña. Fotos confirmadas por Camila: PE_1 de frente (27 %),
  PE_2 de canto y corrida de la esquina (no detectada), PE_3 en diagonal (63 %).
- Bloques de cierre (resultado de 1 partícula, Fase 5, Limitaciones, Conclusiones, Trabajo
  futuro y Resumen): `claude/bloques_cierre.tex` (22-oct). Figura `una_particula_orientacion.png`.
- La referencia es con agua limpia; salió 12 % más baja que el 20-oct (1760 contra 2002)
  por un cambio de la sesión, no por la partícula. No afecta la clasificación (umbral relativo).
- Evidencia: `evidencias/una_particula_2026-10-22.txt`.
- Fotos del 22-oct (28-oct): `MONITOR` con agua limpia, PE_1, PE_2, PE_3, partícula de 1 × 1 mm
  con regla y chip 2 con regla. Lo decisivo es que la partícula quede justo en el haz y de
  frente: la misma partícula pasó de bloquear el 73 % de la luz a no detectarse.
- Medidas del chip 2 leídas en las fotos con regla: ≈ 75 × 25 mm (portaobjetos estándar);
  canal ≈ 3 mm de ancho (2 mm de profundidad, dos capas de ~1 mm).
- **Partículas de la campaña: las dos miden 2 × 1 mm** (dato de Camila, 28-oct). Foto junto a la
  regla: `particulas_pe_regla.jpg` (recorte `foto_particulas_pe.jpg` para la Tabla 9).
- Tabla 9 (28-oct): Camila prefiere no tomar más fotos. Hay 3 listas (agua estéril, cámara de
  ABS y partículas); las otras celdas quedan sin foto por ahora.
- Tabla de costos: Camila envía los costos que no son de impresión; el material de impresión
  de la cámara (gramos de filamento y precio) lo consulta con quien les imprime.
- Paquete para GitHub (`subir_a_github.zip`, 28-oct): README nuevo con resultados, evidencias,
  fotos, tabla consolidada, docs y figuras.

## Decisiones tomadas

1. Alimentación unificada a 3.3 V desde la Pico, sin divisor en la salida del OPT101.
2. LED controlado por transistor (un GPIO no puede dar la corriente del LED).
3. Calentamiento de 180 s dentro de `MEASURE`.
4. Umbral de saturación del sensor: 3050 cuentas (provisional, falta confirmarlo con la Pico).
5. Columna `sem_dV` agregada (v0.2.0) para distinguir el ruido por lectura de la incertidumbre de la media.
6. Agua de referencia: "Agua estéril para inyección" Corpaul (Laboratorios Medifarma), 500 mL.
7. Tope en el tubo, ángulo fijo, chip marcado, regla de descarte definida antes de medir.
8. La unidad de análisis estadístico es **el llenado** (un ΔV de SUMMARY por llenado).
9. Tubo tapado durante las mediciones (14-oct): el fondo bajó de 38 a ~22 cuentas.
10. Se mantiene el **orden alternado**: las partículas salen del chip (3 de 3 en cada llenado).
11. Control de burbujas (protocolo rev. 2, 14-oct): volver a llenar sin esperar si hay
    burbuja en la zona del sensor; revisión y foto al sacar el chip en todos los llenados;
    análisis principal con todos los llenados y secundario sin los que tenían burbuja al sacar;
    `MONITOR` de cierre en cada sesión. **Pendiente de revisar con Diego.**
12. Si se mueve el sensor o el LED, se alinea con `MONITOR` buscando el máximo de ΔV,
    sin pasar de 3050 en `mu_light` (protocolo, sección 8). Posición del OPT101 marcada
    en el tubo y fijada (18-oct).
13. Campaña principal: chip 1 con 6 + 6 (cerrada por la filtración); réplica con el chip 2
    (3 + 3). Para combinar sesiones o chips se usa ΔV como % de la referencia de la sesión.

## Muestra de PE del piloto

- Campaña (18 y 20-oct): **2 partículas de 2 × 1 mm** cada una. Piloto del 14-oct:
  3 partículas: 1 × 2 mm, 3 × 1 mm y 1 × 2 mm, de color **azul oscuro** (elegido por su
  mayor absorción). PENDIENTE: origen y transparencia.
- Las partículas oscuras son un caso favorable; el PE del ambiente suele ser transparente o
  blanco → limitación y trabajo futuro (probar con PE transparente).
- Método de ubicación en la campaña: a mano, procurando que al menos una partícula quede
  frente al sensor. **No se cambia hasta terminar la campaña.** En cada llenado de PE se
  anota la orientación (de pie o acostada) y se toma foto.
- Se cargan con pipeta plástica de 3 mm. El PE flota (densidad ~0.92–0.96 g/cm³).
- En el piloto se ubicaron a mano frente al sensor (mejor caso).
- 14-oct: en los tres llenados se recuperaron las 3 partículas.

## Pendientes

1. ~~Réplica con el chip 2~~ **Hecha el 20-oct (5 + 5).** Texto original: `MONITOR` de referencia + 3 limpias + 3 PE
   alternados (`c2_limpia_01`…, `c2_pe_01`…), mismas 2 partículas y misma forma de ubicarlas.
   Muestra que el resultado no depende de un solo chip. Se combina con el chip 1 usando el
   % de la referencia de cada sesión (decidido antes de medir con el chip 2).
   Antes: curado completo del pegante (24 h o lo que diga el empaque), prueba de fugas
   (10 min lleno sobre papel seco) y, si se puede, un chip de repuesto.
   Tamaños de las 2 partículas: 2 × 1 mm cada una (confirmado el 28-oct).
2. Pruebas de sensibilidad, en la misma sesión después de la campaña: 1 partícula
   (`pe1_01`–`pe1_03`) y otro color, ideal transparente o blanco (`pecolor_01`–`pecolor_03`,
   2 partículas). Cambiar una sola cosa a la vez.
2b. **Descartada (20-oct):** prueba de burbuja intencional. Camila no logró dejar una burbuja
   en el haz: cuesta formarla y siempre se va hacia la salida del canal. Es una observación
   útil para la tesis: con el chip inclinado, el aire tiende a salir solo de la zona de medición.
   Texto original: `MONITOR` sin burbuja, con burbuja en la zona
   del sensor y lejos de ella). En el documento, las burbujas van breves: una fila en la
   tabla de problemas y soluciones y una frase en limitaciones.
3. Documentar la causa exacta de la falla del LED del 13-oct (R_LED = 470 Ω ya quedó documentada el 18-oct).
4. Confirmar el umbral de saturación: durante la alineación del 17-oct, sin chip,
   `mu_light` se quedó en ~3150 (ΔV ~3130), coherente con los ~3128 medidos con el
   multímetro. Falta una medición dedicada para cerrarlo.
5. Según el piloto: campaña formal (~10 llenados por grupo) o modificar la cámara para
   llenar sin sacar el chip (diseño pareado).
6. **Después de la campaña:** prueba de las L impresas en 3D como mejora (OE1: que el canal
   lleve las partículas a la zona del sensor sin ubicarlas a mano). `MONITOR` de referencia
   con las L + 3 limpias + 3 PE alternados, sin ubicar el PE a mano, con IDs `L_limpia_xx` y
   `L_pe_xx` (otro prefijo, para no mezclarlos con la campaña). Revisar burbujas en el tope.
7. Después de la campaña: PCB y piezas estéticas en 3D, y verificación del prototipo final
   (`MONITOR` + 3 limpias + 3 PE). No desarmar la protoboard hasta verificar la PCB.
8. Código: ver la sección 7 de `CLAUDE.md`. El caso de `limpia_03` confirma que hay que
   revisar el criterio `RUIDO_ALTO` en la v0.3.
9. **Validar el WiFi en el hardware** (`docs/plan_wifi.md`, sección 7, ~30 min): `MONITOR 20`
   con el WiFi apagado y encendido (ΔV debe cambiar menos de 1 %), y una referencia, un llenado
   limpio y uno con PE desde el celular, con la Pico en un cargador. Guardar en
   `evidencias/wifi_<fecha>.txt`. Si no cumple: plan B (apagar la radio durante `MEASURE`).

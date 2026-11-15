# Plan: ver y manejar las mediciones desde el celular (WiFi del Pico 2 W)

Propuesto y aprobado el 5-nov-2026. **Implementado en el firmware 0.2.1** el mismo día y
**validado en el hardware el 14-nov-2026** con el prototipo final (`evidencias/wifi_2026-11-14.txt`):

- A contra B (mismo llenado, MEASURE con calentamiento): ΔV −0,10 % con el WiFi encendido. Cumple
  el criterio de menos de 1 %. Se usó MEASURE en vez de `MONITOR 20` porque al reiniciar la Pico
  el LED se enfría y el MONITOR no tiene calentamiento.
- Con el WiFi encendido, `sigma_light` bajó de ~18 a ~2,3 cuentas. Lo más probable es que el
  regulador de 3,3 V de la Pico salga del modo de ahorro (que mete rizado) cuando el chip de
  WiFi consume más.
- C: con la Pico arrancando sola (sin Thonny), la referencia (BASELINE), un PE (77,5 %,
  *PE probable*) y la descarga del CSV funcionaron desde el celular.
- Desde entonces `WIFI_ENABLED = True`.

## 1. Qué se quiere

Medir sin computador: la Pico crea su propia red WiFi, el celular se conecta y en el navegador
se ve la medición en vivo, el resultado de cada llenado y los botones para medir. Sirve para la
sustentación y como avance en la portabilidad, que en la tesis quedó parcial.

**Incluye (v1):**
- Red WiFi propia de la Pico (modo punto de acceso). No necesita internet ni router.
- Página con:
  - estado en vivo;
  - gráfica de ΔV;
  - veredicto de cada llenado (T_rel frente a la referencia, umbral de 80 %);
  - tabla de la sesión;
  - mensajes del firmware;
  - descarga del CSV.
- Botones: referencia, medir, monitor de 20 s y detener. El ID se escribe en la página.
- Arranque automático al conectar la Pico a la corriente.

**No incluye:** internet o nube, pantalla física, batería, conectar la Pico al WiFi de la casa o
la universidad (se puede agregar después) ni cambios en la adquisición.

## 2. Cómo se usaría

1. Conectar la Pico a un cargador de celular, o al computador si se quiere ver también la salida
   por USB.
2. Esperar unos 5 s. Aparece la red **Detector-PE**.
3. Conectar el celular con la contraseña. Si el celular dice "esta red no tiene internet", elegir
   **mantener la conexión**. Si la página no carga, apagar los datos móviles.
4. Abrir **http://192.168.4.1** en el navegador.
5. Seguir el mismo protocolo de siempre:
   - Verificación con **Monitor 20 s** y agua limpia.
   - **Tomar referencia**, con agua limpia.
   - Un llenado por medición: escribir el ID (o tocar la sugerencia `limpia_N` / `pe_N`) y
     **Medir**. Cada medición tarda unos 3 min 20 s.
   - Al terminar cada llenado, la página muestra T_rel y si es *Agua limpia* o *PE probable*.
6. Al final, **Monitor 20 s** de cierre y **Descargar CSV**.

## 3. Cómo funciona por dentro

```
 Celular (navegador)                         Pico 2 W
 ────────────────────                         ──────────────────────────────────────────
 Abre la página ───── GET  /            ───►  io_wifi.py  (red WiFi + servidor pequeño)
 Cada ~1,5 s ──────── GET  /api/estado  ───►    responde con el estado que guarda session.py
 Botones ──────────── POST /api/cmd     ───►    valida con parse_command() y se lo pasa a main.py
 Descargar ────────── GET  /api/csv     ───►    envía el archivo de la sesión

 main.py ── adq.py ── stats.py ── record.py      (adq, stats y record NO cambian)
    └── todo lo que sale: USB (igual que hoy) + archivo en la Pico + session.py
```

**La página es otro teclado.** Los botones mandan los mismos comandos que hoy se escriben en
Thonny (`SET ID=pe_13`, `MEASURE`, `BASELINE`, `MONITOR 20`, `STOP`). Esos comandos pasan por el
mismo `parse_command()`, así que valen las mismas reglas y los mismos mensajes de error.

**No interrumpe la adquisición.** El servidor no usa hilos ni `asyncio`. `main.py` le da un turno
en los mismos puntos donde hoy revisa si llegó `STOP`:
- en espera, cada 10 ms;
- durante una medición, entre repeticiones, nunca dentro de un bloque de 1000 muestras.

Mientras se mide, la página se actualiza cada ~2 s, que es lo que dura una repetición. Si una
petición llega a mitad de un bloque, espera en la cola del WiFi hasta el siguiente turno; no se
pierde.

> ¿Por qué no un framework como Microdot con `asyncio`? Porque el firmware es secuencial y mide
> el tiempo con `ticks_us()`. Pasarlo a `asyncio` obligaría a reescribir `main.py` y `adq.py`.
> El turno (`poll`) sigue el mismo patrón que `stop_requested()`, que ya está probado en el
> hardware.

**Los datos no se pierden.**
- Por USB sale exactamente lo mismo que hoy.
- Además, todo se copia a un archivo en la Pico, `/datos/sesion_NNN.csv` (uno por cada arranque),
  con el mismo formato de la Shell de Thonny: filas CSV y líneas que empiezan con `#`. El análisis
  de siempre (`comment="#"`) lo lee igual.
- Si el celular se desconecta, la medición sigue y el archivo queda guardado.

**Se puede apagar.** Con `WIFI_ENABLED = False`, el firmware se comporta exactamente como en la
campaña.

## 4. Contrato entre la página y la Pico

| Ruta | Método | Qué hace |
|---|---|---|
| `/` | GET | Envía `firmware/web/index.html` desde la memoria de la Pico, por partes |
| `/api/estado` | GET | Estado actual en JSON (abajo) |
| `/api/cmd` | POST | Cuerpo en texto plano con un comando, p. ej. `MEASURE`. Responde `{"ok": true}` o `{"ok": false, "msg": "..."}` |
| `/api/csv` | GET | El archivo de la sesión (`text/csv`) |
| cualquier otra | GET | 404 (`/favicon.ico` responde 204) |

Ejemplo de `/api/estado` mientras se mide:

```json
{
  "fw": "0.2.1", "id": "pe_10", "estado": "midiendo", "run": "R006", "baseline": 0,
  "t": 0, "t_total": 0, "rep": 3, "m": 10,
  "ultimo": {"dV": 412.6, "mu_dark": 22.9, "mu_light": 435.5, "sigma_light": 6.1},
  "serie": [[2001.2, "c"], [1999.8, "r"], [412.6, "r"]],
  "ref": {"dV": 2001.7, "run": "R001"},
  "umbral": 0.8,
  "llenados": [
    {"run": "R001", "id": "ref", "dV": 2001.7, "sem": 0.22, "t_rel": 1.0,
     "veredicto": "ref", "calidad": "OK", "baseline": 1},
    {"run": "R002", "id": "limpia_8", "dV": 1991.7, "sem": 0.19, "t_rel": 0.995,
     "veredicto": "limpia", "calidad": "OK", "baseline": 0}
  ],
  "msgs": ["INICIO R006 ID=pe_10 M=10 baseline=0", "CALENTAMIENTO TERMINADO"]
}
```

- `estado` puede ser `espera`, `calentando`, `midiendo` o `monitor`.
  - En `calentando` y en `monitor` se llenan `t` y `t_total`, en segundos.
  - En `midiendo` se llenan `rep` y `m`.
- Cada punto de `serie` es `[ΔV, tipo]`, con tipo `c` (calentamiento), `r` (repetición) o
  `m` (monitor). Se guardan los últimos 120.
- **Veredicto:**
  - T_rel = ΔV / ΔV_ref.
  - Si T_rel < 0,80, el veredicto es `pe` (PE probable); si no, `limpia`.
  - Sin referencia, el veredicto es `null`.
  - Si la calidad es `SATURADO` o `ERROR`, el veredicto es `invalido` (regla de descarte del
    protocolo). `RUIDO_ALTO` sí se clasifica.
  - La regla es la misma de la campaña. La calcula la Pico (`session.py`) y la página solo
    la muestra.

## 5. Cambios archivo por archivo

| Archivo | Cambio | Corre en | Tests |
|---|---|---|---|
| `adq.py`, `stats.py`, `record.py` | **Ninguno** | — | Los de siempre |
| `io_serial.py` | **Ninguno** (se reutiliza `parse_command`) | — | Los de siempre |
| `config.py` | Agrega `WIFI_AP_SSID = "Detector-PE"`, `WEB_PORT = 80`, `WEB_PAGE_PATH`, `WEB_CLIENT_TIMEOUT_S = 0.5`, `WEB_SERIES_POINTS = 120`, `SESSION_DIR = "/datos"` y `T_REL_THRESHOLD = 0.80`. `FW_VERSION` pasa a `"0.2.1"` para saber qué datos se tomaron con esta versión; el CSV no cambia. `WIFI_ENABLED` ya existía y queda en `False` | PC y Pico | Indirectos |
| `firmware/session.py` (nuevo) | Guarda lo que muestra la página: estado, progreso, últimos puntos, llenados, referencia, T_rel, veredicto y últimos mensajes. Lo entrega como diccionario para el JSON. Lógica pura | PC y Pico | `tests/test_session.py` |
| `firmware/io_wifi.py` (hoy vacío) | `parse_http_request()`, lógica pura. `WebServer` (solo en la Pico): crea la red, socket no bloqueante, rutas y archivo de la sesión | Parser: PC y Pico. `WebServer`: solo Pico | `tests/test_io_wifi.py` (parser) |
| `firmware/web/index.html` (nuevo, **ya hecho**) | La página. Sin librerías externas, porque el celular no tiene internet en esa red | Celular | Demo y revisión visual |
| `firmware/main.py` | Le da turno al servidor en `run()`, `stop_requested()`, `warmup()` y `cmd_monitor()`. Avisa a `session` del estado, los puntos y el resultado. Copia la salida al USB y al archivo | Pico | Prueba en hardware |
| `firmware/secrets.py` (no se sube a GitHub) y `firmware/secrets_ejemplo.py` | `WIFI_AP_PASSWORD`, de mínimo 8 caracteres. Si falta, se informa con `#ERROR` y el firmware sigue sin WiFi | Pico | — |
| `pico/main.py` (nuevo) | Arranque automático. Se copia a la raíz de la Pico: `from firmware.main import main` y `main()` | Pico | — |
| `README.md`, `docs/protocolo_medicion.md`, `docs/estado_del_proyecto.md` | Sección "Medir desde el celular" y la entrada de la prueba | — | — |

## 6. Decisiones tomadas (5-nov)

1. **Referencia: `BASELINE`** (botón *Tomar referencia*, ID `ref`). Mide igual que `MEASURE`, con
   180 s de calentamiento y 10 repeticiones, así que es más comparable con los llenados que el
   promedio del `MONITOR` que se usó en la campaña.
2. **Red:** `Detector-PE`. La contraseña la eligen los estudiantes en `firmware/secrets.py`
   (mínimo 8 caracteres).
3. **Botones en la página:** sí. Sin ellos seguiría haciendo falta el computador.
4. **Arranque automático:** sí (`pico/main.py` → `/main.py`). Thonny lo sigue pudiendo detener
   con *Stop*.
5. **`WIFI_ENABLED = False` hasta la validación** de la sección 7.

## 7. Prueba de validación en el hardware (~30 min)

Sirve para comprobar que el WiFi no cambia la medición. El chip de WiFi consume corriente a
picos, y el OPT101 y el LED se alimentan del mismo 3,3 V de la Pico.

1. Con `WIFI_ENABLED = False` (como viene) y el chip con agua limpia, `MONITOR 20` desde Thonny.
   Anotar el ΔV promedio y `sigma_light`.
2. Con `WIFI_ENABLED = True`, reiniciar la Pico, conectar el celular con la página abierta y
   hacer `MONITOR 20` sin mover nada. Anotar lo mismo.
   **Criterio:** el ΔV cambia menos de 1 % y `sigma_light` queda parecido (~1 % de la señal).
   Como referencia, la variación entre llenados es de ~4 % y el umbral está en 80 %.
3. Pasar la Pico a un cargador de celular, sin el computador. Desde el celular, hacer una
   referencia, un llenado limpio y uno con PE. Revisar que:
   - el veredicto sea el correcto;
   - el CSV se descargue y se abra;
   - si el computador está conectado, por USB salga lo mismo.
4. `MONITOR 20` de cierre.
5. Guardar todo en `evidencias/wifi_<fecha>.txt`.

**Si el paso 2 no cumple:** el plan B es apagar la radio durante `MEASURE` y prenderla al
terminar. La página se desconecta durante la medición y muestra el resultado al reconectarse; la
medición queda igual a la de la campaña.

## 8. Riesgos y cómo se manejan

| Riesgo | Manejo |
|---|---|
| Ruido del WiFi en la señal | Prueba de la sección 7 y plan B |
| El celular se pasa a los datos móviles porque la red "no tiene internet" | Elegir "mantener la conexión" o apagar los datos móviles (paso 3 de la sección 2) |
| Memoria de la Pico | La página (~36 KB, con el simulador de la demo incluido) se envía por partes desde el archivo. El estado ocupa ~2 KB y se guardan máximo 120 puntos |
| Una falla al arrancar en automático | El firmware informa los errores con `#ERROR` y no se cae; Thonny lo detiene con *Stop* |
| Una power bank que se apaga sola porque el consumo es muy bajo | Probar la que tengan o usar un cargador de pared |
| Dos celulares conectados a la vez | Funciona, pero solo uno debería mandar comandos |
| HTTP sin cifrar | Es una red local con contraseña y sin datos sensibles |

## 9. Orden de trabajo

| # | Qué | Commit sugerido |
|---|---|---|
| 1 | `session.py` + tests (en el PC) | `feat(session): estado de la sesion para la pagina web` |
| 2 | Parser HTTP de `io_wifi.py` + tests | `feat(wifi): parser de peticiones http` |
| 3 | `web/index.html` (ya hecha) | `feat(web): pagina de visualizacion` |
| 4 | `WebServer`, `main.py`, `config.py`, `secrets_ejemplo.py`, `pico/main.py`; pytest en verde (83 + nuevos) | `feat(wifi): servidor web y arranque automatico` |
| 5 | Prueba de validación, evidencia y documentación | `docs(wifi): validacion en hardware` |

**Avance (5-nov):** los pasos 1 a 4 están hechos y probados en el PC (140 tests). Falta el paso 5.

**Reparto:** el código lo escribe Claude. Ustedes suben `firmware/` y `pico/main.py` a la Pico con
Thonny, crean `secrets.py` con la contraseña y hacen la prueba de la sección 7.

## 10. Para la sustentación

- **Qué decir:** el prototipo permite ver la medición en tiempo real desde el celular, sin
  computador, con el mismo procesamiento y el mismo criterio de clasificación de la campaña.
- **Demo en vivo:** una medición dura ~3 min 20 s. Conviene llevar la referencia ya tomada y
  mostrar en vivo un solo llenado de PE. No se recomienda bajar el calentamiento para la demo,
  porque el resultado ya no sería comparable con la campaña.
- **Documento:** si se valida antes de la entrega, cabe un párrafo corto (van 65 de 70 páginas).
  Si no, queda como una línea en Trabajos futuros.

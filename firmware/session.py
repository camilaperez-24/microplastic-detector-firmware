"""
session.py — Estado de la sesión para la página web
====================================================

Guarda lo que muestra la página del celular: qué está haciendo el
firmware (espera, calentando, midiendo, monitor), cómo va, los últimos
valores de ΔV, los llenados medidos con su veredicto y los últimos
mensajes. main.py le avisa cada cosa que pasa; io_wifi.py le pide el
estado con to_dict() y lo envía como JSON.

Reglas:
- Lógica pura: no toca hardware ni imprime. Se prueba con pytest en el PC.
- No calcula estadística de los bloques (eso es stats.py): recibe los
  valores ya calculados.
- El veredicto usa la misma regla de la campaña:
      T_rel = ΔV / ΔV_referencia
      T_rel < umbral (0.80)  →  "pe"     (PE probable)
      T_rel >= umbral        →  "limpia"

Contrato del JSON: docs/plan_wifi.md, sección 4.

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""


# ============================================================
# 1. CONSTANTES
# ============================================================

MODE_IDLE = "espera"
MODE_WARMUP = "calentando"
MODE_MEASURE = "midiendo"
MODE_MONITOR = "monitor"
"""Valores del campo "estado" del JSON (los lee la página)."""

KIND_WARMUP = "c"
KIND_REPETITION = "r"
KIND_MONITOR = "m"
"""Tipo de cada punto de la gráfica: calentamiento, repetición o monitor."""

VERDICT_CLEAN = "limpia"
VERDICT_PE = "pe"
VERDICT_REF = "ref"
VERDICT_INVALID = "invalido"
"""Veredictos posibles de un llenado (None = sin referencia todavía)."""

INVALID_QUALITY_PREFIXES = ("SATURADO", "ERROR")
"""Calidades con las que el protocolo descarta el llenado (sección 3, regla 3).
RUIDO_ALTO no descarta: con PE la señal es baja y el criterio no aplica."""


# ============================================================
# 2. REGLA DE CLASIFICACIÓN (funciones puras)
# ============================================================

def relative_transmission(dv, dv_ref):
    """Calcula T_rel = dv / dv_ref.

    Devuelve None si no hay referencia o si la referencia no es positiva
    (una referencia de 0 o negativa no tiene sentido físico).
    """
    if dv_ref is None or dv_ref <= 0:
        return None
    return dv / dv_ref


def classify(t_rel, threshold):
    """Veredicto de un llenado a partir de T_rel.

    Devuelve None si t_rel es None, "pe" si t_rel < threshold
    y "limpia" en otro caso (justo en el umbral cuenta como limpia,
    igual que en la campaña: PE si ΔV < 80 % de la referencia).
    """
    if t_rel is None:
        return None
    if t_rel < threshold:
        return VERDICT_PE
    return VERDICT_CLEAN


def is_invalid_quality(quality):
    """True si la calidad obliga a descartar el llenado (SATURADO o ERROR)."""
    for prefix in INVALID_QUALITY_PREFIXES:
        if quality.startswith(prefix):
            return True
    return False


def _r(value, decimals):
    """Redondea si es un número; deja pasar None. Hace el JSON más corto."""
    if value is None:
        return None
    return round(value, decimals)


# ============================================================
# 3. ESTADO DE LA SESIÓN
# ============================================================

class Session:
    """Todo lo que la página necesita saber, en un solo lugar.

    Uso típico desde main.py:
        s = Session("0.2.1", threshold=0.80, max_points=120)
        s.set_sample_id("pe_01")
        s.start_warmup("R002", is_baseline=False, total_s=180, m=10)
        s.update_elapsed(30.2)
        s.add_point(1850.3, "c")
        s.start_measure()
        s.set_rep(1)
        s.add_point(1851.0, "r")
        s.add_result("R002", "pe_01", 841.5, 0.12, "OK", False)
        s.to_idle()
        s.to_dict()   # → diccionario listo para json.dumps
    """

    def __init__(self, fw_version, threshold, max_points, max_msgs=8, max_fills=60):
        """
        Parámetros
        ----------
        fw_version : str   — versión del firmware (se muestra en la página).
        threshold  : float — umbral de T_rel (0.80 = 80 %).
        max_points : int   — puntos de ΔV que se guardan para la gráfica.
        max_msgs   : int   — mensajes del firmware que se guardan.
        max_fills  : int   — llenados que se guardan (protege la memoria).
        """
        self.fw_version = fw_version
        self.threshold = threshold
        self.max_points = max_points
        self.max_msgs = max_msgs
        self.max_fills = max_fills

        self.sample_id = ""
        self.mode = MODE_IDLE
        self.run_id = None
        self.is_baseline = False
        self.t_s = 0.0
        self.t_total_s = 0
        self.rep = 0
        self.m = 0
        self.last = None      # último punto: dV, mu_dark, mu_light, sigma_light
        self.points = []      # [[dV, tipo], ...] para la gráfica
        self.ref = None       # {"dV": ..., "run": ...}
        self.fills = []       # llenados medidos (diccionarios)
        self.msgs = []        # últimos mensajes del firmware

    # --------------------------------------------------------
    # Muestra y mensajes
    # --------------------------------------------------------

    def set_sample_id(self, sample_id):
        """ID de muestra vigente (el que se fijó con SET ID=)."""
        self.sample_id = sample_id

    def add_msg(self, text):
        """Guarda un mensaje del firmware; se conservan los últimos max_msgs."""
        self.msgs.append(text)
        while len(self.msgs) > self.max_msgs:
            self.msgs.pop(0)

    # --------------------------------------------------------
    # Cambios de estado
    # --------------------------------------------------------

    def start_warmup(self, run_id, is_baseline, total_s, m):
        """Empieza una medición (MEASURE o BASELINE) por el calentamiento."""
        self.mode = MODE_WARMUP
        self.run_id = run_id
        self.is_baseline = is_baseline
        self.t_s = 0.0
        self.t_total_s = total_s
        self.rep = 0
        self.m = m

    def update_elapsed(self, t_s):
        """Segundos transcurridos del calentamiento o del monitor."""
        self.t_s = t_s

    def start_measure(self):
        """Termina el calentamiento: empiezan las M repeticiones."""
        self.mode = MODE_MEASURE
        self.rep = 1

    def set_rep(self, rep):
        """Repetición en curso (1..m)."""
        self.rep = rep

    def start_monitor(self, total_s):
        """Empieza un MONITOR de total_s segundos."""
        self.mode = MODE_MONITOR
        self.run_id = None
        self.is_baseline = False
        self.t_s = 0.0
        self.t_total_s = total_s
        self.rep = 0

    def to_idle(self):
        """Vuelve a espera (al terminar, cancelar o por un error)."""
        self.mode = MODE_IDLE
        self.rep = 0
        self.t_s = 0.0
        self.t_total_s = 0

    def is_busy(self):
        """True si hay una medición o un monitor en curso."""
        return self.mode != MODE_IDLE

    # --------------------------------------------------------
    # Datos
    # --------------------------------------------------------

    def add_point(self, dv, kind, mu_dark=None, mu_light=None, sigma_light=None):
        """Agrega un punto de ΔV a la gráfica (uno por repetición).

        kind: KIND_WARMUP, KIND_REPETITION o KIND_MONITOR.
        """
        self.points.append([_r(dv, 1), kind])
        while len(self.points) > self.max_points:
            self.points.pop(0)
        self.last = {
            "dV": _r(dv, 1),
            "mu_dark": _r(mu_dark, 1),
            "mu_light": _r(mu_light, 1),
            "sigma_light": _r(sigma_light, 1),
        }

    def add_result(self, run_id, sample_id, mean_dv, sem_dv, quality, is_baseline):
        """Registra el resultado (fila SUMMARY) de una medición terminada.

        Si es BASELINE, ese ΔV pasa a ser la referencia de la sesión
        (salvo que la calidad sea SATURADO o ERROR).
        Devuelve el diccionario del llenado agregado.
        """
        invalid = is_invalid_quality(quality)
        if is_baseline:
            t_rel = 1.0 if not invalid else None
            verdict = VERDICT_REF if not invalid else VERDICT_INVALID
            if not invalid:
                self.ref = {"dV": _r(mean_dv, 1), "run": run_id}
        else:
            ref_dv = self.ref["dV"] if self.ref is not None else None
            t_rel = relative_transmission(mean_dv, ref_dv)
            if invalid:
                verdict = VERDICT_INVALID
            else:
                verdict = classify(t_rel, self.threshold)

        fill = {
            "run": run_id,
            "id": sample_id,
            "dV": _r(mean_dv, 1),
            "sem": _r(sem_dv, 3),
            "t_rel": _r(t_rel, 4),
            "veredicto": verdict,
            "calidad": quality,
            "baseline": 1 if is_baseline else 0,
        }
        self.fills.append(fill)
        while len(self.fills) > self.max_fills:
            self.fills.pop(0)
        return fill

    # --------------------------------------------------------
    # Salida para la página
    # --------------------------------------------------------

    def to_dict(self):
        """Estado completo en el formato que espera la página (JSON)."""
        return {
            "fw": self.fw_version,
            "id": self.sample_id,
            "estado": self.mode,
            "run": self.run_id,
            "baseline": 1 if self.is_baseline else 0,
            "t": _r(self.t_s, 1),
            "t_total": self.t_total_s,
            "rep": self.rep,
            "m": self.m,
            "ultimo": self.last,
            "serie": self.points,
            "ref": self.ref,
            "umbral": self.threshold,
            "llenados": self.fills,
            "msgs": self.msgs,
        }

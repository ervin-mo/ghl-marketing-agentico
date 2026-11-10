#!/usr/bin/env python3
"""ghl.py — el marketing de una subcuenta de GoHighLevel, manejado por un agente (o por ti) desde la terminal.

Una sola herramienta, sin instalar nada (Python 3.9+ y su biblioteca estándar). Usa el token de
integración privada (PIT) de la subcuenta. Probado en vivo el 10-nov-2026.

  python3 ghl.py conectar                  # guía para cargar el PIT de una subcuenta (una vez)
  python3 ghl.py ayuda                     # todos los comandos

Seguridad por diseño:
  · Todo lo que publica, programa, gasta o borra exige --si. Sin --si solo enseña lo que haría.
  · Crear un post sin --programar lo deja en BORRADOR (no sale a ninguna red).
  · Nunca imprime el PIT ni los tokens de Facebook que GHL devuelve en algunas respuestas.
"""
import argparse, csv, datetime as dt, getpass, hashlib, json, mimetypes, os, re, shutil, stat, subprocess, sys, \
    time, uuid
import urllib.error, urllib.parse, urllib.request

VERSION = "1.3.2"
BASE = "https://services.leadconnectorhq.com"
ADP = BASE + "/ad-publishing/facebook"
V_SOCIAL = "2021-07-28"      # Social Planner, medios, blogs, correos, enlaces, usuarios, subcuenta
V_ADS = "v3"                 # Ad Manager (anuncios)
AQUI = os.path.dirname(os.path.abspath(__file__))


def _escribible(d):
    """True si de verdad se puede escribir ahí (los sandbox de los agentes dicen que sí y luego niegan)."""
    try:
        os.makedirs(d, exist_ok=True)
        prueba = os.path.join(d, f".prueba-{os.getpid()}")
        with open(prueba, "w") as h:
            h.write("ok")
        os.remove(prueba)
        return True
    except OSError:
        return False


def _dir_datos():
    """Dónde viven subcuentas, PIT (si no hay Llavero), perfil, fichas y metas.
    1) GHL_MARKETING_DIR · 2) .ghl-datos/ dentro de esta carpeta, si ya existe · 3) ~/.config/ghl-marketing si se puede
    escribir · 4) si no (un agente en sandbox, como Codex, que solo deja escribir en la carpeta del proyecto),
    .ghl-datos/ dentro de esta carpeta, copiando lo que ya hubiera en ~/.config/ghl-marketing."""
    if os.environ.get("GHL_MARKETING_DIR"):
        return os.environ["GHL_MARKETING_DIR"]
    local = os.path.join(AQUI, ".ghl-datos")
    casa = os.path.join(os.path.expanduser("~"), ".config", "ghl-marketing")
    if os.path.isdir(local):
        return local
    if _escribible(casa):
        return casa
    try:
        os.makedirs(local, exist_ok=True)
        if os.path.isdir(casa):
            for x in os.listdir(casa):
                if x in ("respaldos", "actualizacion.json"):
                    continue
                src, dst = os.path.join(casa, x), os.path.join(local, x)
                (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)
        try:
            os.chmod(local, stat.S_IRWXU)
        except OSError:
            pass
    except OSError:
        pass
    return local


DIR = _dir_datos()
CUENTAS = os.path.join(DIR, "cuentas.json")
BITACORA = os.path.join(DIR, "bitacora.jsonl")
CAMPANAS = os.path.join(DIR, "campanas")

# alias corto → nombre de plataforma en GHL
REDES = {"fb": "facebook", "facebook": "facebook", "ig": "instagram", "instagram": "instagram",
         "tiktok": "tiktok", "tt": "tiktok", "linkedin": "linkedin", "li": "linkedin", "threads": "threads",
         "google": "google", "gbp": "google", "gmb": "google", "youtube": "youtube", "yt": "youtube",
         "pinterest": "pinterest", "x": "twitter", "twitter": "twitter", "bluesky": "bluesky"}

# Scopes que conviene marcar al crear el PIT (ver docs/PIT.md)
SCOPES = {
    "Subcuenta y usuarios": ["locations.readonly", "users.readonly"],
    "Redes (Social Planner)": ["socialplanner/account.readonly", "socialplanner/post.readonly",
                               "socialplanner/post.write", "socialplanner/category.readonly",
                               "socialplanner/tag.readonly", "socialplanner/statistics.readonly",
                               "socialplanner/csv.readonly", "socialplanner/csv.write"],
    "Medios": ["medias.readonly", "medias.write"],
    "Anuncios (Ad Manager)": ["adPublishing.readonly", "adPublishing.write"],
    "Blogs": ["blogs/list.readonly", "blogs/posts.readonly", "blogs/author.readonly",
              "blogs/category.readonly", "blogs/check-slug.readonly", "blogs/post.write", "blogs/post-update.write"],
    "Correos": ["emails/builder.readonly", "emails/schedule.readonly"],
    "Enlaces y marca": ["links.readonly", "brand-boards/design-kit.readonly"],
    "CRM: embudo y atención (solo lectura)": ["contacts.readonly", "opportunities.readonly", "conversations.readonly",
                                             "conversations/message.readonly"],
}


# ───────────────────────────── utilidades ─────────────────────────────
class Alto(Exception):
    pass


def die(msg, code=1):
    raise Alto(msg)


def oculto(o):
    """Quita tokens de cualquier respuesta (GHL devuelve tokens de página en /integration)."""
    if isinstance(o, dict):
        return {k: ("[OCULTO]" if "oken" in k.lower() or k.lower() in ("secret", "password") else oculto(v))
                for k, v in o.items()}
    if isinstance(o, list):
        return [oculto(x) for x in o]
    return o


def jprint(o, limite=None):
    s = json.dumps(oculto(o), ensure_ascii=False, indent=1)
    if limite and len(s) > limite:
        s = s[:limite] + f"\n… (cortado; {len(s)} caracteres. Usa --json-completo o filtra)"
    print(s)


def texto(t):
    """Los agentes suelen mandar '\\n' literal: se convierte en salto de línea real."""
    if t is None:
        return None
    return t.replace("\\n", "\n").replace("\\t", "\t")


def leer_texto(args, campo="texto"):
    v = getattr(args, campo, None)
    f = getattr(args, campo + "_archivo", None)
    if f:
        with open(f, encoding="utf-8") as h:
            return h.read().strip()
    return texto(v)


def guardar_json(ruta, data):
    tmp = ruta + ".tmp"
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as h:
            json.dump(data, h, ensure_ascii=False, indent=1)
        os.replace(tmp, ruta)
    except PermissionError:
        raise Alto(f"No tengo permiso para guardar en {os.path.dirname(ruta)}. Si esto lo corre un agente en sandbox, "
                   "pídele que lo vuelva a correr con permisos elevados, o corre el comando en tu terminal.")
    try:
        os.chmod(ruta, stat.S_IRUSR | stat.S_IWUSR)
        os.chmod(os.path.dirname(ruta), stat.S_IRWXU)
    except OSError:
        pass


def bitacora(evento, **kw):
    try:
        os.makedirs(DIR, exist_ok=True)
        with open(BITACORA, "a", encoding="utf-8") as h:
            h.write(json.dumps({"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                "evento": evento, **kw}, ensure_ascii=False) + "\n")
    except OSError:
        print("⚠️  No pude anotar en la bitácora (sin permiso de escritura).", file=sys.stderr)


def huella(*partes):
    return hashlib.sha256("|".join(map(str, partes)).encode()).hexdigest()[:16]


def repetido(h, minutos=30):
    if not os.path.exists(BITACORA):
        return False
    lim = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutos)
    with open(BITACORA, encoding="utf-8") as f:
        for l in f:
            try:
                e = json.loads(l)
            except ValueError:
                continue
            if e.get("huella") == h and dt.datetime.fromisoformat(e["ts"]) > lim:
                return True
    return False


# ───────────────────────────── cuentas (credenciales) ─────────────────────────────
LLAVERO = "ghl-marketing"


def llavero_disponible():
    if sys.platform == "darwin" and shutil.which("security"):
        return "macos"
    if sys.platform.startswith("linux") and shutil.which("secret-tool"):
        return "linux"
    return None


def llavero_guardar(alias, pit):
    """Guarda el PIT en el Llavero del sistema. Devuelve True si quedó ahí."""
    t = llavero_disponible()
    try:
        if t == "macos":
            if not re.fullmatch(r"[A-Za-z0-9_\-]+", pit) or not re.fullmatch(r"[a-z0-9\-]+", alias):
                return False   # caracteres raros: mejor archivo protegido que arriesgar el comando
            # «security -i» lee el comando por stdin: el PIT no aparece en la lista de procesos
            r = subprocess.run(["security", "-i"], input=f'add-generic-password -U -s {LLAVERO} -a {alias} '
                               f'-l "GHL PIT {alias}" -w {pit}\n', capture_output=True, text=True)
            return llavero_leer(alias) == pit
        if t == "linux":
            subprocess.run(["secret-tool", "store", f"--label=GHL PIT · {alias}", "service", LLAVERO,
                            "account", alias], input=pit.encode(), check=True, capture_output=True)
            return True
    except (subprocess.CalledProcessError, OSError):
        pass
    return False


def llavero_leer(alias):
    t = llavero_disponible()
    try:
        if t == "macos":
            return subprocess.run(["security", "find-generic-password", "-s", LLAVERO, "-a", alias, "-w"],
                                  check=True, capture_output=True, text=True).stdout.strip()
        if t == "linux":
            return subprocess.run(["secret-tool", "lookup", "service", LLAVERO, "account", alias],
                                  check=True, capture_output=True, text=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        pass
    return None


def llavero_borrar(alias):
    t = llavero_disponible()
    try:
        if t == "macos":
            subprocess.run(["security", "delete-generic-password", "-s", LLAVERO, "-a", alias], capture_output=True)
        elif t == "linux":
            subprocess.run(["secret-tool", "clear", "service", LLAVERO, "account", alias], capture_output=True)
    except OSError:
        pass


def cargar_cuentas():
    if os.path.exists(CUENTAS):
        with open(CUENTAS, encoding="utf-8") as h:
            return json.load(h)
    return {"default": None, "cuentas": {}}


def cuenta_activa(alias=None):
    """Orden: --cuenta → variables GHL_PIT + GHL_LOCATION_ID → la cuenta por defecto."""
    if not alias and os.environ.get("GHL_PIT") and os.environ.get("GHL_LOCATION_ID"):
        return {"alias": "env", "pit": os.environ["GHL_PIT"], "location_id": os.environ["GHL_LOCATION_ID"],
                "user_id": os.environ.get("GHL_USER_ID"), "zona": os.environ.get("GHL_ZONA") or "UTC",
                "nombre": "(variables de entorno)"}
    c = cargar_cuentas()
    alias = alias or os.environ.get("GHL_CUENTA") or c.get("default")
    if not c["cuentas"] and not alias:
        die("Todavía no hay ninguna subcuenta conectada. Corre: python3 ghl.py conectar  (guía: docs/PIT.md)")
    if not alias or alias not in c["cuentas"]:
        disponibles = ", ".join(c["cuentas"]) or "ninguna"
        die(f"No hay subcuenta conectada con ese nombre ({alias}). Disponibles: {disponibles}. "
            "Corre: python3 ghl.py conectar")
    return con_pit(alias, c["cuentas"][alias])


def con_pit(alias, datos):
    d = {"alias": alias, **datos}
    if not d.get("pit"):
        d["pit"] = llavero_leer(alias)
        if not d["pit"]:
            die(f"No encuentro el PIT de «{alias}» en el Llavero (o tu agente no tiene permiso de leerlo). Vuelve a "
                "conectarla desde aquí mismo: python3 ghl.py conectar")
    return d


def todas_las_cuentas(lista=None):
    """[(alias, cuenta)] de todas las conectadas, o solo las de --cuentas a,b."""
    c = cargar_cuentas()
    if not c["cuentas"]:
        die("Todavía no hay ninguna subcuenta conectada. Corre: python3 ghl.py conectar")
    pedidas = [x.strip() for x in lista.split(",")] if lista else list(c["cuentas"])
    faltan = [x for x in pedidas if x not in c["cuentas"]]
    if faltan:
        die(f"No conectadas: {', '.join(faltan)}. Disponibles: {', '.join(c['cuentas'])}")
    return [(x, c["cuentas"][x]) for x in pedidas]


class Ghl:
    def __init__(self, cuenta):
        self.c = cuenta
        self.loc = cuenta["location_id"]
        self._tok = cuenta["pit"]

    def call(self, method, path, body=None, params=None, version=V_SOCIAL, raw=None, ctype="application/json",
             intentos=3):
        url = path if path.startswith("http") else BASE + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}, safe=",:")
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        for i in range(intentos):
            req = urllib.request.Request(url, method=method, data=data)
            for k, v in {"Authorization": f"Bearer {self._tok}", "Version": version, "Accept": "application/json",
                         "Content-Type": ctype, "User-Agent": f"ghl-marketing-agentico/{VERSION}"}.items():
                req.add_header(k, v)
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    t = r.read().decode()
                    try:
                        return r.status, json.loads(t) if t else {}
                    except ValueError:
                        return r.status, {"raw": t[:2000]}
            except urllib.error.HTTPError as e:
                t = e.read().decode()
                if e.code in (429, 502, 503, 504) and i < intentos - 1 and method == "GET":
                    time.sleep(3 * (i + 1)); continue
                try:
                    return e.code, json.loads(t)
                except ValueError:
                    return e.code, {"raw": t[:600]}
            except urllib.error.URLError as e:
                if i < intentos - 1:
                    time.sleep(3 * (i + 1)); continue
                return 0, {"error": f"sin conexión: {e.reason}"}
        return 0, {"error": "sin respuesta"}

    def ok(self, method, path, **kw):
        s, r = self.call(method, path, **kw)
        if s not in (200, 201):
            die(explica(s, r, path))
        return r

    # ── medios ──
    def subir(self, ruta):
        if not os.path.exists(ruta):
            die(f"No existe el archivo: {ruta}")
        b = "----ghlmk" + uuid.uuid4().hex
        ct = mimetypes.guess_type(ruta)[0] or "application/octet-stream"
        nombre = re.sub(r"[^\w.\-]+", "-", os.path.basename(ruta))
        with open(ruta, "rb") as h:
            contenido = h.read()
        partes = [f"--{b}\r\nContent-Disposition: form-data; name=\"hosted\"\r\n\r\nfalse\r\n".encode(),
                  f"--{b}\r\nContent-Disposition: form-data; name=\"name\"\r\n\r\n{nombre}\r\n".encode(),
                  f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nombre}\"\r\n"
                  f"Content-Type: {ct}\r\n\r\n".encode(), contenido, f"\r\n--{b}--\r\n".encode()]
        s, r = self.call("POST", "/medias/upload-file", raw=b"".join(partes),
                         ctype=f"multipart/form-data; boundary={b}", intentos=1)
        if s not in (200, 201) or not r.get("url"):
            die(f"No se pudo subir {ruta}: " + explica(s, r, "/medias/upload-file"))
        return {"url": r["url"], "fileId": r.get("fileId"), "type": ct}


SIN_RED = ("Sin internet en este entorno. Si la computadora sí tiene internet, el que no tiene es TU AGENTE (su sandbox "
           "bloquea la red; pasa con Codex). Agente: vuelve a correr este mismo comando pidiendo permisos elevados / fuera "
           "del sandbox, con la justificación «ghl.py necesita internet para hablar con la API de GoHighLevel», y dile a la "
           "persona que lo apruebe. Detalle: AGENTS.md → «Si eres Codex». Persona: prueba el mismo comando en tu terminal.")


def explica(s, r, path=""):
    """Traduce los errores de GHL a qué hacer."""
    r = oculto(r)
    msg = r.get("message") if isinstance(r, dict) else r
    if isinstance(msg, list):
        msg = "; ".join(map(str, msg))
    msg = str(msg or r)[:400]
    pista = ""
    if s == 401 and "scope" in msg.lower():
        pista = "Al PIT le falta un permiso (scope). En GHL: Settings → Private Integrations → tu token → Edit → " \
                "marca el scope que falta → Update. El token no cambia. Mira: python3 ghl.py diagnostico"
    elif s == 401 and "access this post" in msg.lower():
        pista = "Ese post no es de esta subcuenta. Revisa --cuenta (python3 ghl.py cuentas)."
    elif s == 401 and "location" in msg.lower():
        pista = "Ese PIT es de otra subcuenta, o el locationId está mal copiado (cópialo de la URL)."
    elif s == 401:
        pista = "PIT inválido o borrado. Crea uno nuevo y corre: python3 ghl.py conectar"
    elif s == 403:
        pista = "El plan de GHL de la agencia no incluye esta función, o tu usuario no tiene acceso."
    elif s == 422 and "Access Token not found" in msg:
        pista = "La subcuenta no tiene Facebook conectado para anuncios. GHL → Marketing → Ad Manager → conectar."
    elif s == 422 and "Ad Account not found" in msg:
        pista = "Falta elegir la cuenta publicitaria: Settings → Integrations → Facebook → Manage → Settings → Ad Account."
    elif s == 422 and "Schedule" in msg:
        pista = "La hora de programación debe ser futura (mínimo +5 minutos)."
    elif s == 429:
        pista = "Demasiadas llamadas: espera unos minutos y repite."
    elif s == 0:
        pista = SIN_RED
    return f"HTTP {s} en {path}: {msg}" + (f"\n   → {pista}" if pista else "")


# ───────────────────────────── conectar / cuentas / diagnóstico ─────────────────────────────
def cmd_conectar(a):
    print("Conectar una subcuenta de GHL. Necesitas su PIT (Settings → Private Integrations) y su locationId "
          "(lo que sigue a /location/ en la URL). Guía: docs/PIT.md\n")
    pit = (a.pit or os.environ.get("GHL_PIT") or getpass.getpass("1/3 · Pega el PIT (no se ve al pegarlo): ")).strip()
    loc = (a.location or input("2/3 · Pega el locationId o la URL de la subcuenta: ")).strip()
    m = re.search(r"/location/([A-Za-z0-9]+)", loc)
    if m:
        loc = m.group(1)
    if not pit.startswith("pit-"):
        print("⚠️  Los PIT empiezan con «pit-». Sigo, pero revisa que no sea otra clave.")
    g = Ghl({"pit": pit, "location_id": loc})
    s, r = g.call("GET", f"/locations/{loc}")
    if s == 200:
        l = r.get("location", {})
        nombre, zona = l.get("name") or loc, l.get("timezone") or "UTC"
        pais = l.get("country")
    elif s == 401 and "scope" in str(r).lower():
        nombre, zona, pais = loc, a.zona or "UTC", None
        print("⚠️  El PIT no trae locations.readonly: no puedo leer el nombre ni la zona horaria (uso", zona + ").")
    else:
        die("No pude validar el PIT: " + explica(s, r, "/locations"))
    alias = a.nombre or re.sub(r"[^a-z0-9]+", "-", nombre.lower()).strip("-")[:30] or "subcuenta"
    user_id = a.usuario
    if not user_id:
        s, u = g.call("GET", "/users/", params={"locationId": loc})
        users = u.get("users", []) if s == 200 else []
        if users:
            print("\nUsuarios de la subcuenta (los posts se crean a nombre de uno):")
            for i, x in enumerate(users, 1):
                print(f"  {i}. {x.get('name') or (x.get('firstName','') + ' ' + x.get('lastName','')).strip()}"
                      f" · {x.get('roles', {}).get('role', '')}")
            el = input(f"3/3 · ¿Cuál eres tú? [1-{len(users)}] (Enter = 1): ").strip() or "1"
            try:
                user_id = users[int(el) - 1]["id"]
            except (ValueError, IndexError):
                die("Número fuera de la lista. Vuelve a correr conectar.")
        else:
            user_id = input("userId (Settings → My Staff → tu fila: la URL trae /team/<userId>/): ").strip()
    c = cargar_cuentas()
    datos = {"location_id": loc, "user_id": user_id, "nombre": nombre, "zona": zona, "pais": pais,
             "conectada": dt.date.today().isoformat()}
    if not a.sin_llavero and llavero_guardar(alias, pit):
        datos["pit_en"] = "llavero"
        donde = "el Llavero del sistema (cifrado)"
    else:
        datos["pit"] = pit
        donde = f"{CUENTAS} (solo tu usuario puede leerlo)"
    c["cuentas"][alias] = datos
    if not c.get("default") or a.default:
        c["default"] = alias
    guardar_json(CUENTAS, c)
    print(f"\n✅ Conectada «{nombre}» como «{alias}» · zona {zona} · el PIT quedó en {donde}.")
    print("\nRevisando qué puede hacer el agente en esta subcuenta…\n")
    cmd_diagnostico(argparse.Namespace(cuenta=alias, json=False, json_completo=False))
    if len(c["cuentas"]) > 1:
        print(f"\nTienes {len(c['cuentas'])} subcuentas. Usa --cuenta {alias} o: python3 ghl.py cuentas --usar {alias}")


def cmd_cuentas(a):
    c = cargar_cuentas()
    if a.usar:
        if a.usar not in c["cuentas"]:
            die(f"No existe «{a.usar}».")
        c["default"] = a.usar; guardar_json(CUENTAS, c); print("Por defecto:", a.usar); return
    if a.quitar:
        c["cuentas"].pop(a.quitar, None)
        llavero_borrar(a.quitar)
        if c.get("default") == a.quitar:
            c["default"] = next(iter(c["cuentas"]), None)
        guardar_json(CUENTAS, c); print("Quitada:", a.quitar); return
    if not c["cuentas"]:
        print("No hay subcuentas. Corre: python3 ghl.py conectar"); return
    for k, v in c["cuentas"].items():
        print(f"{'★' if k == c.get('default') else ' '} {k:<22} {v.get('nombre','')} · {v.get('pais') or ''} · "
              f"{v.get('zona')} · {'🔐 llavero' if v.get('pit_en') == 'llavero' else '📄 archivo'}")
    print("★ = la que se usa si no pones --cuenta")


def _perfiles(g):
    s, r = g.call("GET", f"/social-media-posting/{g.loc}/accounts")
    ids = [x.get("profileId") for x in ((r.get("results") or {}).get("accounts", []) if s == 200 else []) if x.get("profileId")]
    return ids or ["sin-redes"]


def cmd_diagnostico(a):
    g = Ghl(cuenta_activa(a.cuenta)); L = g.loc
    pruebas = [
        ("Subcuenta (locations.readonly)", "GET", f"/locations/{L}", None, None, V_SOCIAL),
        ("Usuarios (users.readonly)", "GET", "/users/", {"locationId": L}, None, V_SOCIAL),
        ("Redes conectadas (socialplanner/account.readonly)", "GET", f"/social-media-posting/{L}/accounts", None, None, V_SOCIAL),
        ("Leer posts (socialplanner/post.readonly)", "POST", f"/social-media-posting/{L}/posts/list", None,
         {"type": "recent", "limit": "1", "skip": "0"}, V_SOCIAL),
        ("Categorías (socialplanner/category.readonly)", "GET", f"/social-media-posting/{L}/categories", None, None, V_SOCIAL),
        ("Métricas de redes (statistics)", "POST", "/social-media-posting/statistics", {"locationId": L},
         {"profileIds": _perfiles(g)}, V_SOCIAL),
        ("Medios (medias.readonly)", "GET", "/medias/files", {"altId": L, "altType": "location", "type": "file", "limit": 1}, None, V_SOCIAL),
        ("Anuncios: lectura (adPublishing.readonly)", "GET", f"{ADP}/integration", {"locationId": L}, None, V_ADS),
        ("Blogs (blogs/list.readonly)", "GET", "/blogs/site/all", {"locationId": L, "skip": 0, "limit": 1}, None, V_SOCIAL),
        ("Plantillas de correo (emails/builder.readonly)", "GET", "/emails/builder", {"locationId": L, "limit": 1}, None, V_SOCIAL),
        ("Campañas de correo (emails/schedule.readonly)", "GET", "/emails/schedule", {"locationId": L, "limit": 1}, None, V_SOCIAL),
        ("Enlaces rastreables (links.readonly)", "GET", "/links/", {"locationId": L}, None, V_SOCIAL),
        ("Brand Board (brand-boards)", "GET", f"/brand-boards/{L}", None, None, V_SOCIAL),
    ]
    print(f"Subcuenta «{g.c.get('nombre')}» ({L})\n")
    for nombre, m, p, prm, body, ver in pruebas:
        s, r = g.call(m, p, body=body, params=prm, version=ver)
        if s in (200, 201):
            print("✅", nombre)
        elif s == 422 and "Access Token not found" in str(r):
            print("🟡", nombre, "— permiso OK, pero no hay Facebook conectado en Ad Manager")
        elif s == 422 and "Ad Account not found" in str(r):
            print("🟡", nombre, "— permiso OK, falta elegir la cuenta publicitaria en Integrations")
        elif s == 404 and "integration" in str(r).lower():
            print("🟡", nombre, "— permiso OK, sin integración")
        elif s == 401:
            print("❌", nombre, "— falta el scope en el PIT")
        else:
            print("⚠️ ", nombre, "—", explica(s, r, p).split("\n")[0][:160])
    for nombre, m, p, prm, body in (
            ("CRM: contactos (contacts.readonly)", "POST", "/contacts/search", None, {"locationId": L, "pageLimit": 1}),
            ("CRM: embudos y oportunidades (opportunities.readonly)", "GET", "/opportunities/pipelines", {"locationId": L}, None)):
        s, r = g.call(m, p, body=body, params=prm)
        print("✅" if s in (200, 201) else "❌", nombre, "" if s in (200, 201) else "— falta el scope (embudo de anuncio a venta)")
    s, r = g.call("GET", "/conversations/search", params={"locationId": L, "limit": 1})
    print("✅" if s == 200 else "❌", "CRM: conversaciones (conversations.readonly)", "" if s == 200 else "— falta el scope (leads sin atender)")
    conv = (r.get("conversations") or [{}])[0].get("id") if s == 200 else None
    if conv:
        s, r = g.call("GET", f"/conversations/{conv}/messages", params={"limit": 1})
        print("✅" if s == 200 else "❌", "CRM: mensajes (conversations/message.readonly)",
              "" if s == 200 else "— falta el scope (tiempo de respuesta)")
    # escritura sin crear nada: un anuncio sin campaña real → 401 si falta el permiso
    s, r = g.call("PUT", f"{ADP}/ads", body={"locationId": L, "campaignId": "0" * 24, "adsetId": "0" * 24}, version=V_ADS)
    print("✅" if s != 401 else "❌", "Anuncios: escritura (adPublishing.write)", "" if s != 401 else "— falta el scope")
    print("\nLos ❌ se arreglan en GHL → Settings → Private Integrations → tu token → Edit → Scopes (docs/PIT.md).")


# ───────────────────────────── REDES (Social Planner) ─────────────────────────────
def cuentas_sociales(g):
    r = g.ok("GET", f"/social-media-posting/{g.loc}/accounts")
    return (r.get("results") or {}).get("accounts", [])


def resolver_redes(g, redes, ids):
    accs = [x for x in cuentas_sociales(g) if x.get("active") and not x.get("deleted") and not x.get("isExpired")]
    if ids:
        sel = [x for x in accs if x["id"] in ids.split(",")]
        if len(sel) != len(ids.split(",")):
            die("Algún id de --cuentas-ids no existe o está vencido. Mira: python3 ghl.py redes cuentas")
        return sel
    if not redes:
        die("Di a qué redes: --redes fb,ig,tiktok,linkedin,threads,google,youtube… (o --cuentas-ids id1,id2)")
    sel = []
    for r in redes.split(","):
        p = REDES.get(r.strip().lower())
        if not p:
            die(f"Red desconocida: {r}. Usa: {', '.join(sorted(set(REDES)))}")
        m = [x for x in accs if x.get("platform") == p]
        if not m:
            die(f"La subcuenta no tiene {p} conectado (o está vencido). Mira: python3 ghl.py redes cuentas")
        if len(m) > 1:
            die(f"Hay {len(m)} cuentas de {p}; elige con --cuentas-ids: " + ", ".join(f"{x['id']} ({x['name']})" for x in m))
        sel += m
    return sel


def _tz(zona):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(zona or "UTC")
    except Exception:
        return dt.timezone.utc


def dia_utc(fecha, zona, fin=False):
    """'AAAA-MM-DD' (día en la zona de la subcuenta) → ISO UTC del inicio o del fin de ese día."""
    try:
        d = dt.date.fromisoformat(fecha)
    except ValueError:
        die(f"Fecha no válida: {fecha} (usa AAAA-MM-DD)")
    t = dt.datetime.combine(d, dt.time(23, 59, 59, 999000) if fin else dt.time(0, 0), tzinfo=_tz(zona))
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def a_utc(cuando, zona):
    """'2026-11-12 10:00' en la zona de la subcuenta → ISO UTC. También acepta '+30m', '+2h', 'mañana 9:00'."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(zona)
    except Exception:
        tz = dt.timezone.utc
    ahora = dt.datetime.now(tz)
    c = cuando.strip().lower()
    m = re.fullmatch(r"\+(\d+)\s*(m|min|h|d)", c)
    if m:
        n, u = int(m.group(1)), m.group(2)
        t = ahora + (dt.timedelta(minutes=n) if u in ("m", "min") else dt.timedelta(hours=n) if u == "h" else dt.timedelta(days=n))
    else:
        m = re.fullmatch(r"(hoy|mañana|manana)\s+(\d{1,2}):(\d{2})", c)
        if m:
            d = ahora.date() + dt.timedelta(days=0 if m.group(1) == "hoy" else 1)
            t = dt.datetime(d.year, d.month, d.day, int(m.group(2)), int(m.group(3)), tzinfo=tz)
        else:
            try:
                t = dt.datetime.fromisoformat(cuando.strip().replace("T", " "))
            except ValueError:
                die("Hora no entendida. Usa '2026-11-12 10:00', 'mañana 9:00', 'hoy 18:30' o '+30m'.")
            if t.tzinfo is None:
                t = t.replace(tzinfo=tz)
    if t < ahora + dt.timedelta(minutes=5):
        die(f"La hora debe ser al menos 5 minutos en el futuro (ahora en {zona}: {ahora:%Y-%m-%d %H:%M}).")
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"), t


def preparar_media(g, lista, subir=True):
    out = []
    for m in [x.strip() for x in (lista or "").split(",") if x.strip()]:
        if m.startswith("http"):
            ct = mimetypes.guess_type(urllib.parse.urlparse(m).path)[0] or "image/jpeg"
            out.append({"url": m, "type": ct})
        elif subir:
            r = g.subir(m)
            out.append({"url": r["url"], "type": r["type"]})
            print(f"   subido a Medios: {os.path.basename(m)}", file=sys.stderr)
        else:
            out.append({"url": f"(se subirá) {m}", "type": mimetypes.guess_type(m)[0] or "?"})
    return out


def resumen_post(p):
    ins = p.get("insights") or {}
    red = p.get("platform")
    if p.get("status") in ("draft", "scheduled") and len(p.get("accountIds") or []) != 1:
        red = f"{len(p.get('accountIds') or [])} redes"   # el post «padre» trae platform=google por defecto
    return {"id": p.get("_id"), "red": red, "estado": p.get("status"),
            "fecha": p.get("publishedAt") or p.get("scheduleDate") or p.get("displayDate"),
            "tipo": p.get("type"), "texto": (p.get("summary") or "")[:120].replace("\n", " "),
            "likes": ins.get("like"), "comentarios": ins.get("comment"), "compartidos": ins.get("share"),
            "liga": p.get("previewLink"), "error": p.get("error"), "padre": p.get("parentPostId")}


def cmd_redes(a):
    g = Ghl(cuenta_activa(a.cuenta)); L = g.loc
    if a.accion in ("post", "editar", "borrar") and not a.id:
        die(f"Falta el id del post: redes {a.accion} <id>  (los ids salen en: redes posts)")
    if a.accion == "cuentas":
        if a.json:
            jprint(cuentas_sociales(g)); return
        for x in cuentas_sociales(g):
            est = "vencida ⚠️" if x.get("isExpired") else ("activa" if x.get("active") else "inactiva")
            print(f"{x.get('platform') or '':<10} {(x.get('name') or ''):<32} {est:<11} vence {str(x.get('expire',''))[:10]}  id={x['id']}")
        return
    if a.accion == "posts":
        body = {"type": a.estado, "limit": str(a.limite), "skip": str(a.saltar), "includeUsers": "false"}
        if a.desde: body["fromDate"] = dia_utc(a.desde, g.c.get("zona"))
        if a.hasta: body["toDate"] = dia_utc(a.hasta, g.c.get("zona"), fin=True)
        if a.cuentas_ids: body["accounts"] = a.cuentas_ids
        if a.formato: body["postType"] = a.formato
        r = g.ok("POST", f"/social-media-posting/{L}/posts/list", body=body)
        posts = (r.get("results") or {}).get("posts") or []
        if a.json:
            jprint(posts, None if a.json_completo else 20000); return
        print(f"{len(posts)} posts ({a.estado}) · total en GHL: {(r.get('results') or {}).get('count')}")
        for p in map(resumen_post, posts):
            print(f"· {str(p['fecha'])[:16]} {p['red']:<9} {p['estado'] or '':<10} ❤{p['likes'] or 0} 💬{p['comentarios'] or 0}"
                  f" ↗{p['compartidos'] or 0}  {p['texto'][:70]}  [{p['id']}]" + (f"  ERROR: {p['error']}" if p['error'] else ""))
        return
    if a.accion == "post":
        r = g.ok("GET", f"/social-media-posting/{L}/posts/{a.id}")
        jprint((r.get("results") or {}).get("post", r), None if a.json_completo else 6000); return
    if a.accion == "metricas":
        ids = [x.get("profileId") for x in cuentas_sociales(g) if x.get("profileId")]
        body = {"profileIds": ids}
        if a.redes:
            body["platforms"] = [REDES.get(x.strip(), x.strip()) for x in a.redes.split(",")]
        r = g.ok("POST", "/social-media-posting/statistics", params={"locationId": L}, body=body)
        res = r.get("results") or {}
        if a.json:
            jprint(res); return
        t, b = res.get("totals") or {}, res.get("breakdowns") or {}
        print(f"Últimos 7 días ({', '.join(res.get('dayRange', []))}), cambio % contra los 7 anteriores:\n")
        print(f"  Impresiones {t.get('impressions')} ({b.get('impressions',{}).get('totalChange')}%) · "
              f"Alcance {b.get('reach',{}).get('total')} ({b.get('reach',{}).get('totalChange')}%) · "
              f"Likes {t.get('likes')} · Comentarios {t.get('comments')} · Seguidores nuevos {t.get('followers')} · Posts {t.get('posts')}")
        for red, v in (b.get("impressions", {}).get("platforms") or {}).items():
            e = (b.get("engagement") or {}).get(red, {})
            alc = (b.get("reach", {}).get("platforms") or {}).get(red, {})
            print(f"  {red:<10} impresiones {v.get('value')} ({v.get('change')}%) · alcance {alc.get('value')} · "
                  f"likes {e.get('likes')} · comentarios {e.get('comments')} · compartidos {e.get('shares')}")
        print("\n  Por día (impresiones):", res.get("postPerformance", {}).get("impressions"))
        dem = res.get("demographics") or {}
        if any((dem.get("age", {}).get("totals") or {}).values()):
            print("  Edades:", dem["age"]["totals"], "· Género:", {k: v.get("percentage") for k, v in dem["gender"]["totals"].items()})
        return
    if a.accion == "top":
        posts, skip = [], 0
        while len(posts) < a.cuantos_leer:
            body = {"type": "published", "limit": "50", "skip": str(skip), "includeUsers": "false"}
            if a.desde: body["fromDate"] = dia_utc(a.desde, g.c.get("zona"))
            if a.hasta: body["toDate"] = dia_utc(a.hasta, g.c.get("zona"), fin=True)
            r = g.ok("POST", f"/social-media-posting/{L}/posts/list", body=body)
            lote = (r.get("results") or {}).get("posts") or []
            posts += lote; skip += 50
            if len(lote) < 50: break
        filas = [resumen_post(p) for p in posts]
        for f in filas:
            for k in ("likes", "comentarios", "compartidos"):
                try:
                    f[k] = int(f[k] or 0)
                except (TypeError, ValueError):
                    f[k] = 0
            f["interaccion"] = f["likes"] + 2 * f["comentarios"] + 3 * f["compartidos"]
        filas.sort(key=lambda f: f["interaccion"], reverse=True)
        if a.json:
            jprint(filas[:a.limite]); return
        print(f"Top {a.limite} de {len(filas)} posts publicados (interacción = likes + 2×coment. + 3×compartidos):")
        for f in filas[:a.limite]:
            print(f"· {f['interaccion']:>4}  {str(f['fecha'])[:10]} {f['red']:<9} ❤{f['likes'] or 0} 💬{f['comentarios'] or 0} ↗{f['compartidos'] or 0}"
                  f"  {f['texto'][:60]}  {f['liga'] or ''}")
        return
    if a.accion == "categorias":
        jprint(g.ok("GET", f"/social-media-posting/{L}/categories").get("results")); return
    if a.accion == "tags":
        jprint(g.ok("GET", f"/social-media-posting/{L}/tags").get("results")); return
    if a.accion == "subir":
        for f in a.archivos:
            r = g.subir(f); print(f"✅ {f} → {r['url']}  (fileId {r['fileId']})")
        return
    if a.accion == "revisar" and a.programados:
        ficha = leer_ficha(g.c["alias"])
        res = revisar_programados(g, a.dias or 14, ligas=not a.sin_ligas, ficha=ficha)
        if a.json:
            jprint([{"post": resumen_post(p), "revision": [{"nivel": n, "texto": x} for n, x in r]} for p, r in res]); return
        malos = 0
        for p, r in res:
            f = fecha_local(p, g.c.get("zona")); x = resumen_post(p)
            print(f"\n· {f:%a %d-%m %H:%M} · {x['red']} · {x['texto'][:70]}  [{x['id']}]" if f else f"\n· {x['texto'][:70]}")
            imprimir_revision(r, "  revisión")
            malos += any(n == "🔴" for n, _ in r)
        print(f"\n{len(res)} publicaciones programadas en {a.dias or 14} días · {malos} con problemas graves (🔴)."
              if res else f"No hay nada programado en los próximos {a.dias or 14} días.")
        return
    if a.accion in ("crear", "editar", "revisar"):
        return crear_post(g, a)
    if a.accion == "lote":
        return crear_lote(g, a)
    if a.accion == "borrar":
        s, r = g.call("GET", f"/social-media-posting/{L}/posts/{a.id}")
        p = (r.get("results") or {}).get("post", {}) if s == 200 else {}
        print(f"Post {a.id}: estado {p.get('status')} · {p.get('platform')} · {(p.get('summary') or '')[:80]}")
        if p.get("status") == "published":
            print("⚠️  Ya está PUBLICADO: borrarlo solo lo quita de GHL, NO de la red social (eso es a mano en la red).")
        if not a.si:
            print("Para borrarlo repite con --si."); return
        r = g.ok("DELETE", f"/social-media-posting/{L}/posts/{a.id}")
        bitacora("post-borrado", cuenta=g.c["alias"], post=a.id); print("✅ borrado de GHL"); return


def crear_post(g, a):
    L = g.loc
    sel = resolver_redes(g, a.redes, a.cuentas_ids)
    resumen = leer_texto(a) or ""
    if a.formato == "story" and resumen:
        print("ℹ️  Las historias no llevan texto: se manda vacío.", file=sys.stderr); resumen = ""
    a.formato = a.formato or "post"
    if a.formato == "story" and not a.media:
        die("Una historia necesita una imagen o un video (--media).")
    if not resumen and not a.media:
        die("Falta el texto (--texto o --texto-archivo) o la imagen/video (--media).")
    programar = bool(a.cuando)
    if programar:
        fecha_utc, local = a_utc(a.cuando, g.c.get("zona") or "UTC")
    else:
        local = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30)
        fecha_utc = local.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    zona = g.c.get("zona")
    if getattr(a, "_recientes", None) is None:
        a._recientes = textos_recientes(g, excluir=a.id if a.accion == "editar" else None)
    medias = [m.strip() for m in (a.media or "").split(",") if m.strip()]
    rev = revisar_post(sel, resumen, medias, a.formato, local if programar else None, leer_ficha(g.c["alias"]),
                       a._recientes, ligas=not a.sin_ligas, primer_comentario=texto(a.primer_comentario), zona=zona)
    estado = "scheduled" if programar else "draft"
    plan = {"subcuenta": g.c.get("nombre"), "redes": [f"{x['platform']} · {x['name']}" for x in sel],
            "tipo": a.formato, "estado": "PROGRAMADO" if programar else "BORRADOR (no sale a ninguna red)",
            "sale": f"{local:%Y-%m-%d %H:%M} ({g.c.get('zona')})" if programar else "—",
            "texto": resumen[:300] + ("…" if len(resumen) > 300 else ""), "media": a.media or "—",
            "primer_comentario": texto(a.primer_comentario) or "—"}
    print("PLAN:"); jprint(plan)
    imprimir_revision(rev)
    rojos = [x for x in rev if x[0] == "🔴"]
    if a.accion == "revisar":
        print("\n(solo revisión: no se creó nada)"); return bool(not rojos)
    if rojos and programar and not a.forzar:
        print(f"\n⛔ La revisión encontró {len(rojos)} problema(s) que harían fallar o quedar mal la publicación. "
              "Corrígelos; si de verdad debe salir así, repite con --forzar.")
        return False
    if programar and not a.si:
        print("\n⛔ Programar = va a salir publicado a esa hora. Si es correcto, repite el mismo comando con --si.")
        return False
    if a.accion == "editar" and not a.si:
        print("\n⛔ Editar reemplaza el post que ya existe (sin --cuando queda como BORRADOR y se desprograma). "
              "Si es correcto, repite con --si.")
        return False
    h = huella(L, resumen, ",".join(sorted(x["id"] for x in sel)), a.formato, a.media)
    if programar and repetido(h) and not a.repetir:
        die("Ya programaste este mismo post en los últimos 30 min. Si de verdad va dos veces: --repetir.")
    if a.vista_previa:
        print("\n(vista previa: no se creó nada)"); return False
    body = {"accountIds": [x["id"] for x in sel], "summary": resumen, "media": preparar_media(g, a.media),
            "status": estado, "scheduleDate": fecha_utc, "type": a.formato, "userId": g.c.get("user_id")}
    if a.primer_comentario: body["followUpComment"] = texto(a.primer_comentario)
    if a.categoria: body["categoryId"] = a.categoria
    if a.etiquetas: body["tags"] = [t.strip() for t in a.etiquetas.split(",")]
    if not body["userId"]:
        die("Falta el userId de la subcuenta. Vuelve a correr: python3 ghl.py conectar")
    if a.accion == "editar":
        s, r = g.call("PUT", f"/social-media-posting/{L}/posts/{a.id}", body=body)
        pid = a.id
    else:
        s, r = g.call("POST", f"/social-media-posting/{L}/posts", body=body)
        pid = ((r.get("results") or {}).get("post") or {}).get("_id") if isinstance(r, dict) else None
    if s not in (200, 201):
        die(explica(s, r, "posts"))
    bitacora("post-" + ("programado" if programar else "borrador"), cuenta=g.c["alias"], post=pid, huella=h,
             redes=[x["platform"] for x in sel], sale=fecha_utc if programar else None)
    if programar:
        print(f"\n✅ PROGRAMADO en GHL. Post {pid}. Sale {local:%Y-%m-%d %H:%M} ({g.c.get('zona')}). "
              "Programado ≠ publicado: revisa después con  python3 ghl.py redes posts --estado failed")
    else:
        print(f"\n✅ BORRADOR {'actualizado' if a.accion == 'editar' else 'creado'}: {pid}. No sale a ninguna red. Revísalo en GHL → Marketing → Social Planner "
              "o prográmalo con: redes editar " + str(pid) + " … --cuando '…' --si")
    return True


def crear_lote(g, a):
    """Parrilla: un JSON con una lista de posts. Sin --si solo enseña el plan; con --si crea cada uno
    (los que traen "cuando" quedan PROGRAMADOS; los demás, BORRADOR)."""
    if not a.id:
        die("redes lote <parrilla.json>  (formato en ejemplos/parrilla.json)")
    with open(a.id, encoding="utf-8") as h:
        items = json.load(h)
    items = items.get("posts", items) if isinstance(items, dict) else items
    base = os.path.dirname(os.path.abspath(a.id))
    print(f"{len(items)} posts en la parrilla · " + ("CREANDO" if a.si else "solo plan (agrega --si para crearlos)"))
    hechos = 0
    for n, it in enumerate(items, 1):
        print(f"\n── {n}/{len(items)} ──")
        media = ",".join(m if m.startswith("http") or os.path.isabs(m) else os.path.join(base, m)
                         for m in ([it["media"]] if isinstance(it.get("media"), str) else it.get("media") or []))
        sub_a = argparse.Namespace(**{**vars(a), "accion": "crear", "redes": it.get("redes"),
                                      "cuentas_ids": it.get("cuentas"), "texto": it.get("texto"), "texto_archivo": None,
                                      "media": media or None, "cuando": it.get("cuando"),
                                      "formato": it.get("formato", "post"), "primer_comentario": it.get("primer_comentario"),
                                      "categoria": it.get("categoria"), "etiquetas": it.get("etiquetas"),
                                      "vista_previa": not a.si, "_recientes": getattr(a, "_recientes", None)})
        if sub_a._recientes is None:
            a._recientes = sub_a._recientes = textos_recientes(g)
        try:
            if crear_post(g, sub_a) and a.si:
                hechos += 1
        except Alto as e:
            print(f"⚠️  Post {n} no se creó: {str(e).splitlines()[0][:200]}")
    print(f"\nListo: {hechos} de {len(items)} creados." if a.si else
          "\nSolo plan. Si la revisión no marcó 🔴, repite con --si para crearlos.")


# ───────────────────────────── ANUNCIOS (Meta por Ad Manager) ─────────────────────────────
FIELDS = "spend,impressions,clicks,reach,ctr,cpm,cpc,frequency,results"


def _snake(k):
    return ".".join(re.sub(r"(?<!^)(?=[A-Z])", "_", p).lower() for p in k.split("."))


def _fila(o):
    o = o or {}
    res = o.get("results") if isinstance(o.get("results"), dict) else (o.get("resultsBreakdown") or {})
    acc = {_snake(k): v for k, v in (res or {}).items()}
    f = lambda x: float(x) if str(x).replace(".", "", 1).replace("-", "", 1).isdigit() else 0.0
    out = {k: f(o.get(k)) for k in ("spend", "impressions", "clicks", "reach", "ctr", "cpm", "cpc", "frequency")}
    out["conversaciones"] = f(acc.get("onsite_conversion.messaging_conversation_started_7d"))
    out["clics_enlace"] = f(acc.get("link_click"))
    out["leads"] = f(acc.get("lead") or acc.get("onsite_conversion.lead_grouped"))
    out["acciones"] = acc
    return out


def _rango(a, zona=None):
    hoy = dt.datetime.now(_tz(zona)).date()
    if a.dias:
        return (hoy - dt.timedelta(days=a.dias)).isoformat(), (hoy - dt.timedelta(days=1)).isoformat()
    try:
        hasta = dt.date.fromisoformat(a.hasta) if a.hasta else hoy - dt.timedelta(days=1)
        desde = dt.date.fromisoformat(a.desde) if a.desde else hasta - dt.timedelta(days=6)
    except ValueError:
        die("Fechas en formato AAAA-MM-DD.")
    if desde > hasta:
        die(f"--desde ({desde}) es posterior a --hasta ({hasta}).")
    return desde.isoformat(), hasta.isoformat()


def cmd_ads(a):
    g = Ghl(cuenta_activa(a.cuenta)); L = g.loc
    V = {"version": V_ADS}
    if a.accion == "verificar":
        s, i = g.call("GET", f"{ADP}/integration", params={"locationId": L}, **V)
        con = s == 200 and i.get("status") == "connected"
        print("✅" if con else "❌", "Ad Manager conectado", "—", f"cuenta {i.get('fbAdAccountId')} · página {i.get('fbDefaultPageId')}" if con else explica(s, i, "integration"))
        if con:
            s, x = g.call("GET", f"{ADP}/ad-accounts/{i['fbAdAccountId']}", params={"locationId": L}, **V)
            print("✅" if x.get("accountStatus") == "ACTIVE" else "❌", "Cuenta publicitaria", "—", x.get("name"), x.get("accountStatus"), x.get("currency"), x.get("timezoneName"))
        s, r = g.call("GET", f"{ADP}/reporting", params={"locationId": L, "type": "INTEGRATION", "fields": "spend", "startDate": "2026-01-01", "endDate": "2026-01-02"}, **V)
        print("✅" if s == 200 else "❌", "Lectura de reportes (cuenta elegida en Integrations)", "" if s == 200 else "— " + explica(s, r, "reporting").split("\n")[-1])
        s, r = g.call("PUT", f"{ADP}/ads", body={"locationId": L, "campaignId": "0" * 24, "adsetId": "0" * 24}, **V)
        print("✅" if s != 401 else "❌", "Permiso para crear campañas (adPublishing.write)")
        s, ps = g.call("GET", f"{ADP}/pages", params={"locationId": L}, **V)
        for p in ps if isinstance(ps, list) else []:
            print("✅" if p.get("tosAccepted") else "🟡", f"Condiciones de leads · {p.get('name')}",
                  "" if p.get("tosAccepted") else f"— solo para campañas de formulario: https://www.facebook.com/ads/leadgen/tos?page_id={p.get('id')}")
        return
    if a.accion == "cuentas":
        r = g.ok("GET", f"{ADP}/ad-accounts", params={"locationId": L}, **V)
        for x in r if isinstance(r, list) else []:
            print(f"{'★' if x.get('integrationConnected') else ' '} {x.get('id'):<22} {(x.get('name') or ''):<30} {x.get('accountStatus')} {x.get('currency')}")
        print("★ = la que usa la subcuenta"); return
    if a.accion == "reporte":
        s0, u0 = _rango(a, g.c.get("zona"))
        if a.nivel == "cuenta":
            r = g.ok("GET", f"{ADP}/reporting", params={"locationId": L, "type": "INTEGRATION", "startDate": s0, "endDate": u0, "fields": FIELDS}, **V)
            gr = r.get("grouped") or []
            t = _fila(gr[0] if gr else r.get("totals"))
            if a.json: jprint(t); return
            print(f"Cuenta publicitaria · {s0} → {u0}")
            print(f"  Gasto {t['spend']:,.2f} · Impresiones {t['impressions']:,.0f} · Alcance {t['reach']:,.0f} · Clics {t['clicks']:,.0f} "
                  f"· CTR {t['ctr']:.2f}% · CPM {t['cpm']:,.2f} · Frecuencia {t['frequency']:.2f}")
            print(f"  Conversaciones iniciadas {t['conversaciones']:,.0f} · Clics al enlace {t['clics_enlace']:,.0f} · Leads {t['leads']:,.0f}")
            if t["conversaciones"]: print(f"  Costo por conversación {t['spend']/t['conversaciones']:,.2f}")
            return
        p = {"locationId": L, "type": "INTEGRATION", "startDate": s0, "endDate": u0, "fields": FIELDS}
        if a.nivel == "campana":
            r = g.ok("GET", f"{ADP}/reporting/list", params={**p, "listType": "campaigns"}, **V)
            filas = r if isinstance(r, list) else []
            if a.json: jprint(filas); return
            print(f"Campañas · {s0} → {u0} (este nivel no trae alcance ni conversaciones; usa --nivel conjunto)")
            for x in sorted(filas, key=lambda x: -float(x.get("spend") or 0)):
                if float(x.get("spend") or 0) or a.todas:
                    print(f"· {(x.get('name') or '')[:50]:<50} gasto {float(x.get('spend') or 0):>12,.2f} impr {float(x.get('impressions') or 0):>9,.0f} clics {float(x.get('clicks') or 0):>6,.0f}  id={x.get('campaignId') or x.get('id')}")
            return
        if not a.campana:
            die("Para --nivel conjunto|anuncio di de qué campaña: --campana <id de Meta> (sale en --nivel campana).")
        lt = "adsets" if a.nivel == "conjunto" else "ads"
        r = g.ok("GET", f"{ADP}/reporting/list", params={**p, "listType": lt, "campaignId": a.campana}, **V)
        filas = r if isinstance(r, list) else []
        if a.json: jprint(filas); return
        print(f"{'Conjuntos' if lt == 'adsets' else 'Anuncios'} de {a.campana} · {s0} → {u0}")
        ocultas = 0
        for x in filas:
            f = _fila(x)
            if not f["spend"] and not f["impressions"] and not a.todas:
                ocultas += 1; continue
            cpc = f"{f['spend']/f['conversaciones']:,.2f}" if f["conversaciones"] else "—"
            print(f"· {(x.get('name') or '')[:45]:<45} gasto {f['spend']:>11,.2f} impr {f['impressions']:>8,.0f} alc {f['reach']:>8,.0f} "
                  f"clics {f['clicks']:>5,.0f} conv {f['conversaciones']:>4,.0f} c/conv {cpc}")
        if ocultas:
            print(f"({ocultas} sin entrega en el rango; --todas para verlos)")
        return
    if a.accion == "campanas":
        r = g.ok("GET", f"{ADP}/entity", params={"locationId": L, "type": "INTEGRATION", "entityType": "CAMPAIGN", "fetchAll": "true"}, **V)
        for x in r.get("data") or []:
            print(f"· {str(x.get('effectiveStatus') or x.get('status')):<10} {(x.get('name') or '')[:60]:<60} id={x.get('campaignId') or x.get('id')}")
        return
    if a.accion == "buscar":
        r = g.ok("GET", f"{ADP}/targeting/search", params={"locationId": L, "type": a.tipo, "query": a.texto}, **V)
        jprint(r, 5000); return
    if a.accion == "formularios":
        s, i = g.call("GET", f"{ADP}/integration", params={"locationId": L}, **V)
        page = a.pagina or (i.get("fbDefaultPageId") if s == 200 else None)
        if not page: die("Di la página: --pagina <pageId>")
        jprint(g.ok("GET", f"{ADP}/page/{page}/forms", params={"locationId": L, "limit": 50, "projection": "id,name,status,isDraft,locale"}, **V), 6000); return
    if a.accion == "audiencias":
        s, i = g.call("GET", f"{ADP}/integration", params={"locationId": L}, **V)
        act = a.act or (i.get("fbAdAccountId") if s == 200 else None)
        jprint(g.ok("GET", f"{ADP}/custom-audience", params={"locationId": L, "type": "all", "adAccountId": act, "limit": 100, "source": "integration"}, **V), 6000); return
    if a.accion == "pixeles":
        jprint(g.ok("GET", f"{ADP}/pixels", params={"locationId": L, "limit": 100}, **V), 6000); return
    if a.accion == "crear":
        return ads_crear(g, a)
    if a.accion in ("publicar", "estado", "pausar", "reanudar", "borrar"):
        return ads_operar(g, a)


def _textos(lista):
    return [x if isinstance(x, dict) else {"text": texto(x)} for x in (lista or [])]


def _put(g, que, body):
    s, r = g.call("PUT", f"{ADP}/{que}", body={"locationId": g.loc, **body}, version=V_ADS)
    if s != 200:
        die(f"No se pudo crear {que}: " + explica(s, r, que))
    return r


def ads_crear(g, a):
    with open(a.spec, encoding="utf-8") as h:
        spec = json.load(h)
    base = os.path.dirname(os.path.abspath(a.spec))
    rel = lambda f: f if os.path.isabs(f) else os.path.join(base, f)
    print("PLAN de campaña (se crea en BORRADOR, no toca Meta ni gasta):")
    for cj in spec["conjuntos"]:
        print(f"  · conjunto «{cj['name']}» presupuesto {cj.get('budget')} · {len(cj['anuncios'])} anuncio(s)")
    if not a.si:
        print("Para crearla en borrador repite con --si."); return
    estado = {"campana": None, "cuenta": g.c["alias"], "medios": []}
    c = _put(g, "campaigns", {"specialAdCategories": ["NONE"], "isCampaignBudget": False, **spec["campana"]})
    cid = estado["campana"] = c["id"]
    ruta = os.path.join(CAMPANAS, f"{cid}.json")
    guardar_json(ruta, estado)
    for cj in spec["conjuntos"]:
        cj = dict(cj); anuncios = cj.pop("anuncios")
        st = _put(g, "adsets", {"campaignId": cid, **cj})
        for an in anuncios:
            media = []
            for m in an.get("media", []):
                if "archivo" in m:
                    up = g.subir(rel(m["archivo"])); estado["medios"].append(up["fileId"]); guardar_json(ruta, estado)
                    item = {"src": up["url"], "type": "video" if up["type"].startswith("video") else "image"}
                    if item["type"] == "video":
                        if not m.get("miniatura"): die(f"El video {m['archivo']} necesita \"miniatura\" (una imagen).")
                        pu = g.subir(rel(m["miniatura"])); estado["medios"].append(pu["fileId"]); guardar_json(ruta, estado)
                        item.update({"thumbnailUrl": pu["url"], "selectedPoster": 0})
                    for k in ("link", "headline", "description"):
                        if k in m: item[k] = m[k]
                    media.append(item)
                else:
                    media.append(m)
            body = {"campaignId": cid, "adsetId": st["id"], "multiAdvertiserAds": False,
                    "mediaType": an.get("mediaType", "SINGLE"), "cta": an.get("cta", "LEARN_MORE"),
                    **{k: v for k, v in an.items() if k not in ("media", "primaryTexts", "headlines", "descriptions")},
                    "primaryTexts": _textos(an.get("primaryTexts")), "headlines": _textos(an.get("headlines")),
                    "descriptions": _textos(an.get("descriptions")), "media": media}
            _put(g, "ads", body)
    bitacora("campana-borrador", cuenta=g.c["alias"], campana=cid)
    print(f"✅ Campaña en BORRADOR: {cid}. Revísala: python3 ghl.py ads estado {cid}")
    print("   Publicar = arranca a gastar YA (GHL ignora la fecha de inicio): python3 ghl.py ads publicar", cid, "--si")


def _resumen_campana(g, cid):
    s, c = g.call("GET", f"{ADP}/campaign/{cid}", params={"locationId": g.loc, "fields": "adsets,ads"}, version=V_ADS)
    if s != 200: die(explica(s, c, "campaign"))
    out = {"id": cid, "nombre": c.get("name"), "estado": c.get("publishingStatus"), "meta_id": c.get("fbCampaignId"),
           "error": c.get("fbError"), "conjuntos": []}
    for st in c.get("adsets") or []:
        out["conjuntos"].append({"nombre": st.get("name"), "estado": st.get("publishingStatus"), "error": st.get("fbError"),
                                 "rechazo_meta": (st.get("meta") or {}).get("validationError"),
                                 "anuncios": [{"nombre": x.get("name"), "estado": x.get("publishingStatus"), "error": x.get("fbError"),
                                               "rechazo_meta": (x.get("meta") or {}).get("validationError")} for x in st.get("ads") or []]})
    return out


def ads_operar(g, a):
    cid = a.id
    if not cid:
        die(f"Falta el id de la campaña de GHL: ads {a.accion} <id>  (sale al crearla con ads crear)")
    if a.accion == "estado":
        jprint(_resumen_campana(g, cid)); return
    acciones = {"publicar": "publish", "pausar": "pause", "reanudar": "resume"}
    if a.accion in ("publicar", "reanudar", "borrar") and not a.si:
        avisos = {"publicar": "Publicar crea la campaña en Meta y EMPIEZA A GASTAR YA (GHL ignora la fecha de inicio).",
                  "reanudar": "Reanudar vuelve a gastar.", "borrar": "Borrar la quita de Meta (en GHL queda archivada)."}
        print("⛔", avisos[a.accion], "Si es correcto, repite con --si."); return
    if a.accion == "borrar":
        s, r = g.call("DELETE", f"{ADP}/campaigns/{cid}", body={"locationId": g.loc}, version=V_ADS)
        print("borrar →", s, (r or {}).get("message", ""))
        ruta = os.path.join(CAMPANAS, f"{cid}.json")
        if s == 200 and os.path.exists(ruta):
            with open(ruta) as h: est = json.load(h)
            for fid in est.get("medios") or []:
                g.call("DELETE", f"/medias/{fid}", params={"altId": g.loc, "altType": "location"})
        bitacora("campana-borrada", cuenta=g.c["alias"], campana=cid); return
    s, r = g.call("POST", f"{ADP}/campaigns/{cid}/{acciones[a.accion]}", body={"locationId": g.loc}, version=V_ADS)
    if s not in (200, 201): die(explica(s, r, a.accion))
    bitacora("campana-" + a.accion, cuenta=g.c["alias"], campana=cid)
    if a.accion == "publicar":
        t0 = time.time()
        while time.time() - t0 < 180:
            s, p = g.call("GET", f"{ADP}/campaigns/{cid}/publishing-progress", params={"locationId": g.loc}, version=V_ADS)
            if s != 200 or (p.get("isComplete") and p.get("publishingStatus") != "PUBLISHING"): break
            time.sleep(10)
        if a.pausar:
            g.call("POST", f"{ADP}/campaigns/{cid}/pause", body={"locationId": g.loc}, version=V_ADS)
    jprint(_resumen_campana(g, cid))


# ───────────────────────────── datos reutilizables (no detienen el programa) ─────────────────────────────
DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MILES_CON_PUNTO = {"CL", "CO", "AR", "PY", "UY", "ES", "PE", "BO", "VE", "EC", "CR", "BR", "DE", "IT"}
SIN_DECIMALES = {"CL", "CO", "PY", "AR", "UY"}


def dinero(x, pais=None):
    x = float(x or 0)
    if (pais or "").upper() in SIN_DECIMALES:
        t = f"{x:,.0f}"
    else:
        t = f"{x:,.2f}"
    if (pais or "").upper() in MILES_CON_PUNTO:
        t = t.replace(",", "§").replace(".", ",").replace("§", ".")
    return "$" + t


def num(x, pais=None):
    t = f"{float(x or 0):,.0f}"
    return t.replace(",", ".") if (pais or "").upper() in MILES_CON_PUNTO else t


def delta(nuevo, viejo):
    """Cambio porcentual como texto: '+12%', '−30%', 'nuevo' o '—'."""
    nuevo, viejo = float(nuevo or 0), float(viejo or 0)
    if not viejo:
        return "nuevo" if nuevo else "—"
    d = (nuevo - viejo) / viejo * 100
    return f"{'+' if d >= 0 else '−'}{abs(d):.0f}%"


def _hoy(zona):
    return dt.datetime.now(_tz(zona)).date()


def rango_fechas(a, zona, por_defecto=7):
    """(desde, hasta) como date, en la zona de la subcuenta. --mes AAAA-MM, --dias N o --desde/--hasta."""
    hoy = _hoy(zona)
    if getattr(a, "mes", None):
        try:
            y, m = (int(x) for x in a.mes.strip().split("-"))
            ini = dt.date(y, m, 1)
            fin = dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
        except (ValueError, TypeError):
            die(f"Mes no válido: {a.mes} (usa AAAA-MM, por ejemplo 2026-10)")
        hasta = min(fin, hoy - dt.timedelta(days=1))
        if ini > hasta:
            die(f"El mes {a.mes} todavía no tiene días cerrados (hoy es {hoy}).")
        return ini, hasta
    if getattr(a, "dias", None) or not (getattr(a, "desde", None) or getattr(a, "hasta", None)):
        n = getattr(a, "dias", None) or por_defecto
        return hoy - dt.timedelta(days=n), hoy - dt.timedelta(days=1)
    try:
        hasta = dt.date.fromisoformat(a.hasta) if a.hasta else hoy - dt.timedelta(days=1)
        desde = dt.date.fromisoformat(a.desde) if a.desde else hasta - dt.timedelta(days=6)
    except ValueError:
        die("Fechas en formato AAAA-MM-DD.")
    if desde > hasta:
        die(f"--desde ({desde}) es posterior a --hasta ({hasta}).")
    return desde, hasta


def periodo_anterior(desde, hasta):
    n = (hasta - desde).days + 1
    return desde - dt.timedelta(days=n), desde - dt.timedelta(days=1)


def posts_en(g, estado, desde=None, hasta=None, maximo=600):
    """Todos los posts de un estado en el rango (fechas date en la zona de la subcuenta)."""
    out, skip = [], 0
    while len(out) < maximo:
        body = {"type": estado, "limit": "50", "skip": str(skip), "includeUsers": "false"}
        if desde: body["fromDate"] = dia_utc(desde.isoformat(), g.c.get("zona"))
        if hasta: body["toDate"] = dia_utc(hasta.isoformat(), g.c.get("zona"), fin=True)
        s, r = g.call("POST", f"/social-media-posting/{g.loc}/posts/list", body=body)
        if s not in (200, 201):
            raise Alto(explica(s, r, "posts/list"))
        lote = (r.get("results") or {}).get("posts") or []
        out += lote; skip += 50
        if len(lote) < 50:
            break
    return out


def _int(x):
    try:
        return int(x or 0)
    except (TypeError, ValueError):
        return 0


def interaccion(p):
    i = p.get("insights") or {}
    return _int(i.get("like")) + 2 * _int(i.get("comment")) + 3 * _int(i.get("share"))


def fecha_local(p, zona):
    f = p.get("publishedAt") or p.get("scheduleDate") or p.get("displayDate")
    if not f:
        return None
    try:
        return dt.datetime.fromisoformat(f.replace("Z", "+00:00")).astimezone(_tz(zona))
    except ValueError:
        return None


def datos_redes(g, desde, hasta, con_metricas=True):
    zona = g.c.get("zona")
    accs = cuentas_sociales(g)
    ahora = dt.datetime.now(dt.timezone.utc)
    vencidas, por_vencer = [], []
    for x in accs:
        if x.get("deleted"):
            continue
        try:
            exp = dt.datetime.fromisoformat(str(x.get("expire")).replace("Z", "+00:00"))
        except ValueError:
            exp = None
        if x.get("isExpired") or (exp and exp < ahora):
            vencidas.append(f"{x.get('platform')} ({x.get('name')})")
        elif exp and exp < ahora + dt.timedelta(days=7):
            por_vencer.append(f"{x.get('platform')} ({x.get('name')}) vence {exp.astimezone(_tz(zona)):%d-%m}")
    pub = posts_en(g, "published", desde, hasta)
    fal = posts_en(g, "failed", desde, hasta)
    hoy = _hoy(zona)
    prog = posts_en(g, "scheduled", hoy, hoy + dt.timedelta(days=14))
    d = {"redes": len([x for x in accs if not x.get("deleted")]), "vencidas": vencidas, "por_vencer": por_vencer,
         "publicados": len(pub), "interaccion": sum(interaccion(p) for p in pub),
         "likes": sum(_int((p.get("insights") or {}).get("like")) for p in pub),
         "comentarios": sum(_int((p.get("insights") or {}).get("comment")) for p in pub),
         "compartidos": sum(_int((p.get("insights") or {}).get("share")) for p in pub),
         "fallidos": [resumen_post(p) for p in fal], "programados": prog, "posts": pub,
         "por_red": {}, "cuentas": accs}
    for p in pub:
        r = d["por_red"].setdefault(p.get("platform") or "?", {"posts": 0, "interaccion": 0})
        r["posts"] += 1; r["interaccion"] += interaccion(p)
    if con_metricas:
        ids = [x.get("profileId") for x in accs if x.get("profileId")]
        if ids:
            s, r = g.call("POST", "/social-media-posting/statistics", params={"locationId": g.loc}, body={"profileIds": ids})
            d["metricas7"] = (r.get("results") or {}) if s == 200 else None
    return d


def datos_ads(g, desde, hasta, detalle=False):
    """Totales del rango y del periodo anterior. {'sin_ads': motivo} si la subcuenta no tiene Ad Manager listo."""
    L = g.loc
    s, i = g.call("GET", f"{ADP}/integration", params={"locationId": L}, version=V_ADS)
    if s == 401:
        return {"sin_ads": "el PIT no trae adPublishing.readonly"}
    if s != 200:
        return {"sin_ads": "sin Facebook en Ad Manager"}

    def tot(a, b):
        s, r = g.call("GET", f"{ADP}/reporting", params={"locationId": L, "type": "INTEGRATION", "startDate": a.isoformat(),
                                                        "endDate": b.isoformat(), "fields": FIELDS}, version=V_ADS)
        if s != 200:
            raise Alto(explica(s, r, "reporting"))
        gr = r.get("grouped") or []
        return _fila(gr[0] if gr else r.get("totals"))
    try:
        act, ant = tot(desde, hasta), tot(*periodo_anterior(desde, hasta))
    except Alto as e:
        return {"sin_ads": "no se pudo leer la cuenta de reportes (" + str(e).split("\n")[0][:90] + ")"}
    d = {"actual": act, "anterior": ant, "cuenta": i.get("fbAdAccountId"), "campanas": []}
    s, r = g.call("GET", f"{ADP}/reporting/list", params={"locationId": L, "type": "INTEGRATION", "listType": "campaigns",
                                                         "startDate": desde.isoformat(), "endDate": hasta.isoformat(),
                                                         "fields": FIELDS}, version=V_ADS)
    for x in (r if s == 200 and isinstance(r, list) else []):
        if float(x.get("spend") or 0) > 0:
            d["campanas"].append({"id": str(x.get("campaignId") or x.get("id")), "nombre": x.get("name") or "",
                                  "gasto": float(x.get("spend") or 0), "impresiones": float(x.get("impressions") or 0),
                                  "clics": float(x.get("clicks") or 0)})
    d["campanas"].sort(key=lambda c: -c["gasto"])
    if detalle:
        for c in d["campanas"][:8]:
            s, r = g.call("GET", f"{ADP}/reporting/list", params={"locationId": L, "type": "INTEGRATION", "listType": "adsets",
                                                                 "campaignId": c["id"], "startDate": desde.isoformat(),
                                                                 "endDate": hasta.isoformat(), "fields": FIELDS}, version=V_ADS)
            c["conjuntos"] = []
            for x in (r if s == 200 and isinstance(r, list) else []):
                f = _fila(x)
                if f["spend"]:
                    f["nombre"] = x.get("name") or ""
                    c["conjuntos"].append(f)
            for k in ("conversaciones", "leads", "clics_enlace"):
                c[k] = sum(f[k] for f in c["conjuntos"])
            c["alcance"] = sum(f["reach"] for f in c["conjuntos"])
            c["frecuencia_max"] = max([f["frequency"] for f in c["conjuntos"]] or [0])
    return d


SINGULAR = {"conversaciones": "conversación", "leads": "lead", "clics al enlace": "clic al enlace", "resultados": "resultado"}


def resultado_ads(f):
    """El resultado principal de una fila de anuncios: conversaciones, leads o clics al enlace."""
    for k, n in (("conversaciones", "conversaciones"), ("leads", "leads"), ("clics_enlace", "clics al enlace")):
        if f.get(k):
            return f[k], n
    return 0, "resultados"


def alertas_de(g, red, ads, metas=None, atn=None, emb=None, ads_mes=None, dias=7):
    """Lista de (nivel, texto). nivel: 🔴 urgente · 🟡 revisar · 🟢 bien."""
    out = []
    metas = metas or {}
    pais = g.c.get("pais")
    for v in red["vencidas"]:
        out.append(("🔴", f"Red desconectada: {v}. Todo lo programado ahí va a fallar. Reconectar en Social Planner → Settings."))
    for v in red["por_vencer"]:
        out.append(("🟡", f"Conexión por vencer: {v}. Reconectar antes en Social Planner → Settings."))
    if red["fallidos"]:
        ej = red["fallidos"][0]
        out.append(("🔴", f"{len(red['fallidos'])} post(s) fallidos en el periodo (ej.: {ej['red']} «{ej['texto'][:40]}» → {str(ej['error'])[:90]})."))
    zona = g.c.get("zona")
    hoy = _hoy(zona)
    dias_con = {fecha_local(p, zona).date() for p in red["programados"] if fecha_local(p, zona)}
    prox7 = [hoy + dt.timedelta(days=i) for i in range(7)]
    if not red["programados"]:
        out.append(("🔴", "No hay nada programado para los próximos 14 días."))
    elif sum(1 for d in prox7 if d in dias_con) <= 1:
        out.append(("🟡", f"Parrilla delgada: solo {sum(1 for d in prox7 if d in dias_con)} día(s) con publicación en los próximos 7."))
    if red["publicados"] == 0:
        out.append(("🟡", "No se publicó nada en el periodo."))
    if "sin_ads" not in ads:
        a, b = ads["actual"], ads["anterior"]
        ra, n = resultado_ads(a)
        rb, _ = resultado_ads(b)
        if a["spend"] and ra:
            ca, cb = a["spend"] / ra, (b["spend"] / rb if rb else 0)
            if cb and ca > cb * 1.3:
                out.append(("🟡", f"El costo por {SINGULAR[n]} subió {delta(ca, cb)} contra el periodo anterior."))
            elif cb and ca < cb * 0.8:
                out.append(("🟢", f"El costo por {SINGULAR[n]} bajó {delta(ca, cb)}."))
        elif a["spend"] and not ra:
            out.append(("🟡", "Hubo gasto en anuncios sin resultados medidos (conversaciones, leads ni clics)."))
        if b["spend"] and not a["spend"]:
            out.append(("🟡", "Los anuncios dejaron de gastar (el periodo anterior sí gastaba): ¿pausados, sin saldo o rechazados?"))
        if a["frequency"] > 3:
            out.append(("🟡", f"Frecuencia {a['frequency']:.1f}: el público ya vio mucho el anuncio; conviene creativo nuevo."))
        if a["ctr"] and b["ctr"] and a["ctr"] < b["ctr"] * 0.7:
            out.append(("🟡", f"El CTR cayó de {b['ctr']:.2f}% a {a['ctr']:.2f}%: creativo cansado o público equivocado."))
        if metas.get("costo_max") and a["spend"] and ra:
            c = a["spend"] / ra
            if c > metas["costo_max"]:
                out.append(("🔴", f"Costo por {SINGULAR[n]} {dinero(c, pais)}: arriba de la meta ({dinero(metas['costo_max'], pais)})."))
    # programados con problemas (sin revisar ligas, para que sea rápido)
    accs = {x["id"]: x for x in red.get("cuentas") or []}
    malos = []
    ficha = leer_ficha(g.c["alias"])
    for p in red["programados"]:
        cs = [accs[i] for i in p.get("accountIds") or [] if i in accs]
        r = [x for x in revisar_post(cs, p.get("summary"), [m.get("url") for m in p.get("media") or [] if m.get("url")],
                                     p.get("type") or "post", fecha_local(p, zona), ficha, None, False,
                                     p.get("followUpComment"), zona) if x[0] == "🔴"]
        if r or len(cs) < len(p.get("accountIds") or []):
            malos.append((p, r[0][1] if r else "una de sus redes ya no está conectada"))
    if malos:
        out.append(("🔴", f"{len(malos)} publicación(es) programada(s) con problemas (ej.: {malos[0][1][:110]}). "
                          "Detalle: redes revisar --programados"))
    # metas de contenido
    if metas.get("posts_semana"):
        n_piezas = piezas(red["posts"])
        ritmo = n_piezas / max(dias / 7, 1 / 7)
        if n_piezas and ritmo < metas["posts_semana"] * 0.95:
            out.append(("🟡", f"Se publicaron {ritmo:.1f} por semana; la meta es {metas['posts_semana']:g}.".replace(".0 por", " por")))
        prox = piezas([p for p in red["programados"]
                       if fecha_local(p, zona) and fecha_local(p, zona).date() < hoy + dt.timedelta(days=7)])
        if prox < metas["posts_semana"]:
            out.append(("🟡", f"Para los próximos 7 días hay {prox} programada(s); la meta es {metas['posts_semana']:g} por semana."))
    # presupuesto del mes
    if metas.get("gasto_mes") and ads_mes is not None and hoy.day > 1:
        import calendar
        dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
        esperado = metas["gasto_mes"] * (hoy.day - 1) / dias_mes
        proy = ads_mes / max(hoy.day - 1, 1) * dias_mes
        if esperado and ads_mes > esperado * 1.15:
            out.append(("🟡", f"El presupuesto del mes va adelantado: {dinero(ads_mes, pais)} gastado; a este ritmo cierra en "
                              f"{dinero(proy, pais)} (meta {dinero(metas['gasto_mes'], pais)})."))
        elif esperado and ads_mes < esperado * 0.7:
            out.append(("🟡", f"El presupuesto del mes va atrasado: {dinero(ads_mes, pais)} gastado; a este ritmo cierra en "
                              f"{dinero(proy, pais)} (meta {dinero(metas['gasto_mes'], pais)})."))
    # CRM
    if atn and "sin_crm" not in atn and atn["sin_respuesta"]:
        p = atn["sin_respuesta"]
        out.append(("🔴" if len(p) >= 5 or p[0]["horas"] > 24 else "🟡",
                    f"{len(p)} chat(s) esperan respuesta hace más de {duracion(atn['horas'])} (el más viejo: "
                    f"{duracion(p[0]['horas'])}). Ligas: crm atencion"))
    if emb and "sin_crm" not in emb:
        import calendar
        f = calendar.monthrange(hoy.year, hoy.month)[1] / max((hoy - hoy.replace(day=1)).days, 1)
        if metas.get("leads_mes") and emb["leads"] * f < metas["leads_mes"] * 0.8:
            out.append(("🟡", f"Leads del mes: {emb['leads']} hasta ayer; a este ritmo cierra en {emb['leads'] * f:.0f} "
                              f"(meta {metas['leads_mes']:g})."))
        if metas.get("ventas_mes") and emb["ventas"] * f < metas["ventas_mes"] * 0.8:
            out.append(("🟡", f"Ventas del mes: {emb['ventas']} hasta ayer; a este ritmo cierra en {emb['ventas'] * f:.0f} "
                              f"(meta {metas['ventas_mes']:g})."))
        if emb.get("gasto") and not emb["origen"]["anuncios"]:
            out.append(("🟡", "Hay inversión en anuncios, pero ningún lead del CRM quedó marcado como de anuncios: "
                              "configura metas --etiquetas-anuncio para medir el costo por lead y por venta."))
    return out


# ───────────────────────────── CLIENTE: metas y ficha de marca ─────────────────────────────
CLIENTES = os.path.join(DIR, "clientes")

METAS = {  # campo: (tipo, explicación)
    "posts_semana": (float, "publicaciones por semana (un post en varias redes cuenta como 1)"),
    "costo_max": (float, "costo máximo por resultado de anuncios (conversación, lead o clic)"),
    "gasto_mes": (float, "presupuesto de anuncios del mes"),
    "leads_mes": (float, "leads nuevos por mes"),
    "ventas_mes": (float, "ventas por mes"),
    "responder_horas": (float, "horas máximas para contestar un mensaje (por defecto 2)"),
    "etiquetas_anuncio": (list, "etiquetas del CRM que marcan un lead que vino de anuncios"),
    "etapas_venta": (list, "etapas del embudo que cuentan como venta"),
    "pipeline": (str, "nombre o id del embudo (pipeline) que se mide"),
}


def carpeta_cliente(alias):
    return os.path.join(CLIENTES, re.sub(r"[^\w.\-]+", "-", alias or "sin-nombre"))


def alias_activo(alias=None):
    """El alias sin cargar el PIT (para metas y ficha, que viven en tu computadora)."""
    if not alias and os.environ.get("GHL_PIT") and os.environ.get("GHL_LOCATION_ID"):
        return "env"
    c = cargar_cuentas()
    alias = alias or os.environ.get("GHL_CUENTA") or c.get("default")
    if not alias or alias not in c["cuentas"]:
        die(f"No hay subcuenta conectada con ese nombre ({alias}). Disponibles: {', '.join(c['cuentas']) or 'ninguna'}.")
    return alias


def leer_metas(alias):
    r = os.path.join(carpeta_cliente(alias), "metas.json")
    if not os.path.exists(r):
        return {}
    try:
        with open(r, encoding="utf-8") as h:
            return json.load(h)
    except ValueError:
        die(f"El archivo de metas está dañado: {r}")


def leer_perfil():
    if os.path.exists(os.path.join(DIR, "perfil.json")):
        try:
            with open(os.path.join(DIR, "perfil.json"), encoding="utf-8") as h:
                return json.load(h)
        except ValueError:
            return {}
    return {}


def fmt_meta(v):
    return ", ".join(v) if isinstance(v, list) else (f"{v:g}" if isinstance(v, float) else str(v))


def cmd_metas(a):
    campos = {k: getattr(a, k) for k in METAS if getattr(a, k) is not None}
    if not a.cuenta and not campos and not a.quitar:
        c = cargar_cuentas()
        if not c["cuentas"]:
            print("No hay subcuentas conectadas."); return
        for al, v in c["cuentas"].items():
            m = leer_metas(al)
            print(f"■ {v.get('nombre')}  [{al}]")
            print("   " + (" · ".join(f"{k}={fmt_meta(x)}" for k, x in m.items())
                          if m else "sin metas (ejemplo: metas --cuenta " + al + " --posts-semana 3 --costo-max 2000)"))
        return
    alias = alias_activo(a.cuenta)
    m = leer_metas(alias)
    for k, v in campos.items():
        tipo = METAS[k][0]
        if tipo is list:
            m[k] = [x.strip() for x in v.split(",") if x.strip()]
        elif tipo is float:
            try:
                m[k] = float(str(v).replace(".", "").replace(",", ".")) if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", str(v)) \
                    else float(str(v).replace(",", "."))
            except ValueError:
                die(f"--{k.replace('_', '-')} debe ser un número.")
        else:
            m[k] = v
    for k in (a.quitar or "").split(","):
        m.pop(k.strip().replace("-", "_"), None)
    if campos or a.quitar:
        guardar_json(os.path.join(carpeta_cliente(alias), "metas.json"), m)
        print(f"✅ Metas de «{alias}» guardadas.")
    if not m:
        print("Sin metas. Campos posibles:")
        for k, (t, d) in METAS.items():
            print(f"  --{k.replace('_', '-'):<20} {d}")
        return
    for k, v in m.items():
        print(f"  {k:<18} {fmt_meta(v)}   ({METAS.get(k, ('', ''))[1]})")


RE_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F1E6-\U0001F1FF]")
RE_URL = re.compile(r"https?://[^\s)>\]\"']+", re.I)
RE_HASHTAG = re.compile(r"(?<![\w&])#(\w+)", re.U)
RE_USTED = re.compile(r"\b(usted|ustedes|le invitamos|los invitamos|lo invitamos|la invitamos|cont[aá]ctenos|escr[ií]banos|"
                      r"vis[ií]tenos|ll[aá]menos|agende|reserve|conozca|descubra|aproveche)\b", re.I)
RE_TU = re.compile(r"\b(t[uú]|tus|te|cont[aá]ctanos|escr[ií]benos|vis[ií]tanos|ll[aá]manos|agenda|reserva|conoce|descubre|"
                   r"aprovecha)\b", re.I)


def estilo_actual(posts):
    """Cómo escribe hoy la marca, calculado de sus publicaciones (sin IA)."""
    textos = []
    vistos = set()
    for p in posts:
        t = (p.get("summary") or "").strip()
        if t and t[:80] not in vistos:
            vistos.add(t[:80]); textos.append(t)
    if not textos:
        return "- (sin publicaciones con texto para analizar)", "(defínelo: tú o usted)", "", "", "- "
    largos = sorted(len(t) for t in textos)
    med = largos[len(largos) // 2]
    emo = sum(len(RE_EMOJI.findall(t)) for t in textos) / len(textos)
    tags = {}
    for t in textos:
        for h in RE_HASHTAG.findall(t):
            tags[h.lower()] = tags.get(h.lower(), 0) + 1
    top = sorted(tags.items(), key=lambda x: -x[1])[:10]
    us, tu = sum(len(RE_USTED.findall(t)) for t in textos), sum(len(RE_TU.findall(t)) for t in textos)
    trato = ("(no se distingue: defínelo)" if not us and not tu else "usted" if us > tu * 1.3
             else "tú (tuteo)" if tu > us * 1.3 else "mezcla de tú y usted")
    preg = sum("?" in t for t in textos) / len(textos) * 100
    ligas = sum(bool(RE_URL.search(t)) for t in textos) / len(textos) * 100
    con_tags = sum(bool(RE_HASHTAG.search(t)) for t in textos) / len(textos) * 100
    lineas = [f"- Publicaciones analizadas: {len(textos)}",
              f"- Largo típico: {med} caracteres (de {largos[0]} a {largos[-1]})",
              f"- Trato: {trato}",
              f"- Emojis: {emo:.1f} por publicación",
              f"- Hashtags: en {con_tags:.0f} % de las publicaciones" + (f"; los más usados: {' '.join('#' + h for h, _ in top)}" if top else ""),
              f"- Hacen una pregunta: {preg:.0f} % · traen liga: {ligas:.0f} %"]
    emojis = "pocos o ninguno" if emo < 0.5 else ("moderados" if emo < 3 else "muchos")
    return "\n".join(lineas), trato, emojis, f"~{med} caracteres", ("\n".join(f"- #{h}" for h, _ in top[:5]) or "- ")


FICHA = """# Ficha de marca · {nombre}

<!-- La lee el agente antes de escribir o revisar publicaciones de este cliente. Edítala con libertad.
     Respeta solo los títulos «## Palabras prohibidas» y «## Hashtags fijos»: sus listas con guion las lee la
     herramienta y la revisión de publicaciones las aplica. -->

## El negocio
- Qué vende y a quién:
- Ciudad / país: {ciudad}
- Sitio web: {web}
- Redes: {redes}
- Horario, teléfono y dirección que se pueden publicar:
- Diferenciadores (por qué elegirlo):

## Tono
- Trato: {trato}
- Estilo (3 palabras):
- Emojis: {emojis}
- Largo típico: {largo}

## Llamados a la acción preferidos
-

## Hashtags fijos
<!-- Los que deben ir siempre. Sugerencia sacada de lo que ya usa: -->
{hashtags}

## Palabras prohibidas
<!-- Una por línea. Si un post trae alguna, la revisión lo frena. Ej.: «gratis» si nada es gratis, la competencia. -->
-

## Temas que no se tocan
-

## Ejemplos que le gustan al cliente
-
{marca}
## Cómo escribe hoy
<!-- Calculado de sus publicaciones recientes ({fecha}). Se rehace con: ficha --actualizar-estilo -->
{estilo}
"""


def ruta_ficha(alias):
    return os.path.join(carpeta_cliente(alias), "ficha.md")


def leer_ficha(alias):
    """{'texto', 'prohibidas', 'hashtags'} o None si el cliente no tiene ficha."""
    r = ruta_ficha(alias)
    if not os.path.exists(r):
        return None
    with open(r, encoding="utf-8") as h:
        t = h.read()
    t_sin = re.sub(r"<!--.*?-->", "", t, flags=re.S)

    def lista(titulo):
        m = re.search(r"^##\s*" + titulo + r"\s*$(.*?)(?=^##\s|\Z)", t_sin, re.M | re.S | re.I)
        if not m:
            return []
        limpios = [x.strip().strip("«»\"'“”").strip() for x in re.findall(r"^\s*[-*]\s*(.+?)\s*$", m.group(1), re.M)]
        return [x for x in limpios if x]
    return {"texto": t, "prohibidas": lista("Palabras prohibidas"),
            "hashtags": [h.lstrip("#").lower() for x in lista("Hashtags fijos") for h in x.split() if h.startswith("#")]}


def cmd_ficha(a):
    alias = alias_activo(a.cuenta)
    r = ruta_ficha(alias)
    if a.ruta:
        print(r); return
    if a.abrir:
        if not os.path.exists(r):
            die("Todavía no existe. Créala con: python3 ghl.py ficha --crear")
        abre = "open" if sys.platform == "darwin" else ("xdg-open" if shutil.which("xdg-open") else None)
        if sys.platform.startswith("win"):
            os.startfile(r)  # noqa
        elif abre:
            subprocess.run([abre, r])
        print(r); return
    if a.crear or a.actualizar_estilo:
        if os.path.exists(r) and a.crear and not a.rehacer:
            die(f"Ya existe ({r}). Para rehacer solo «Cómo escribe hoy»: --actualizar-estilo. Para empezar de cero: --crear --rehacer")
        if a.actualizar_estilo and not os.path.exists(r):
            die("Todavía no existe. Créala con: python3 ghl.py ficha --crear")
        g = Ghl(cuenta_activa(a.cuenta))
        hoy = _hoy(g.c.get("zona"))
        print("Leyendo las publicaciones de los últimos 90 días…", file=sys.stderr)
        pubs = [p for p in posts_en(g, "published", hoy - dt.timedelta(days=90), hoy, maximo=300) if (p.get("summary") or "").strip()]
        if len(pubs) < 5:
            print("Pocas con texto; amplío a 12 meses…", file=sys.stderr)
            pubs = [p for p in posts_en(g, "published", hoy - dt.timedelta(days=365), hoy, maximo=600) if (p.get("summary") or "").strip()]
        estilo, trato, emojis, largo, tags = estilo_actual(pubs)
        if a.actualizar_estilo:
            with open(r, encoding="utf-8") as h:
                t = h.read()
            nuevo = f"## Cómo escribe hoy\n<!-- Calculado de sus publicaciones recientes ({hoy:%d-%m-%Y}). " \
                    f"Se rehace con: ficha --actualizar-estilo -->\n{estilo}\n"
            t = re.sub(r"^## Cómo escribe hoy.*\Z", lambda _: nuevo, t, flags=re.M | re.S) if "## Cómo escribe hoy" in t \
                else t.rstrip() + "\n\n" + nuevo
            with open(r, "w", encoding="utf-8") as h:
                h.write(t)
            print(f"✅ «Cómo escribe hoy» actualizado en {r}\n\n{estilo}"); return
        s, loc = g.call("GET", f"/locations/{g.loc}")
        l = (loc.get("location") or {}) if s == 200 else {}
        b = l.get("business") or {}
        social = {k.replace("Url", ""): v for k, v in (l.get("social") or {}).items() if isinstance(v, str) and v.startswith("http")}
        s, bb = g.call("GET", f"/brand-boards/{g.loc}")
        marca = ""
        if s == 200 and (bb.get("brandBoards") or []):
            marca = "\n## Marca visual (Brand Board de GHL)\n```\n" + json.dumps(oculto(bb["brandBoards"][0]), ensure_ascii=False)[:900] + "\n```\n"
        t = FICHA.format(nombre=g.c.get("nombre"), ciudad=", ".join(x for x in (b.get("city") or l.get("city"),
                                                                              b.get("country") or l.get("country")) if x),
                         web=b.get("website") or l.get("website") or "",
                         redes=" · ".join(f"{k}: {v}" for k, v in social.items()) or "(ver: redes cuentas)",
                         trato=trato, emojis=emojis, largo=largo, hashtags=tags, marca=marca,
                         fecha=f"{hoy:%d-%m-%Y}", estilo=estilo)
        os.makedirs(os.path.dirname(r), exist_ok=True)
        with open(r, "w", encoding="utf-8") as h:
            h.write(t)
        print(f"✅ Ficha creada: {r}\n   Complétala (qué vende, tono, palabras prohibidas…) o pídele al agente que la llene contigo.\n")
        print(t); return
    f = leer_ficha(alias)
    if not f:
        print(f"«{alias}» no tiene ficha de marca. Créala con: python3 ghl.py ficha --cuenta {alias} --crear"); return
    print(f["texto"])
    print(f"\n({r})")


# ───────────────────────────── REVISIÓN antes de programar ─────────────────────────────
LIMITE_TEXTO = {"twitter": 280, "bluesky": 300, "threads": 500, "pinterest": 500, "google": 1500, "instagram": 2200,
                "tiktok": 2200, "linkedin": 3000, "youtube": 5000, "facebook": 63206}
MAX_MEDIA = {"twitter": 4, "bluesky": 4, "pinterest": 1, "youtube": 1, "google": 1, "instagram": 20, "threads": 20,
             "linkedin": 20, "tiktok": 35}
NECESITA_MEDIA = {"instagram", "tiktok", "youtube", "pinterest"}
RE_RELLENO = re.compile(r"\[(?:link|enlace|url|liga|nombre|precio|fecha|cta|aqu[ií]|insertar|pendiente|texto)[^\]]*\]|"
                        r"\{\{[^}]*\}\}|lorem ipsum|\bTODO\b|\bXXX+\b|<<[^>]*>>|\bTBD\b", re.I)
RE_TELEFONO = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")


def medidas_imagen(ruta):
    """(ancho, alto) leyendo la cabecera de PNG, JPEG, GIF o WebP. None si no se puede."""
    import struct
    try:
        with open(ruta, "rb") as h:
            d = h.read(2_000_000)
        if d[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", d[16:24])
        if d[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", d[6:10])
        if d[:4] == b"RIFF" and d[8:12] == b"WEBP":
            c = d[12:16]
            if c == b"VP8 ":
                return (struct.unpack("<H", d[26:28])[0] & 0x3FFF, struct.unpack("<H", d[28:30])[0] & 0x3FFF)
            if c == b"VP8L":
                b = int.from_bytes(d[21:25], "little")
                return ((b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1)
            if c == b"VP8X":
                return (int.from_bytes(d[24:27], "little") + 1, int.from_bytes(d[27:30], "little") + 1)
        if d[:2] == b"\xff\xd8":
            i = 2
            while i < len(d) - 9:
                if d[i] != 0xFF:
                    i += 1; continue
                m = d[i + 1]
                if m == 0xFF:
                    i += 1; continue
                if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    alto, ancho = struct.unpack(">HH", d[i + 5:i + 9])
                    return ancho, alto
                if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                    i += 2; continue
                i += 2 + struct.unpack(">H", d[i + 2:i + 4])[0]
    except (OSError, Exception):
        return None
    return None


def datos_video(ruta):
    """{'ancho','alto','segundos'} con ffprobe si está instalado; si no, None."""
    if not shutil.which("ffprobe"):
        return None
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height:stream_tags=rotate:format=duration", "-of", "json", ruta],
                           capture_output=True, text=True, timeout=30)
        j = json.loads(r.stdout or "{}")
        st = (j.get("streams") or [{}])[0]
        w, h = st.get("width"), st.get("height")
        if str((st.get("tags") or {}).get("rotate")) in ("90", "270", "-90"):
            w, h = h, w
        return {"ancho": w, "alto": h, "segundos": float((j.get("format") or {}).get("duration") or 0)}
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


_LIGAS = {}


def liga_viva(url):
    """True (abre), False (rota: 404, 410, 5xx o el dominio no existe) o None (no se pudo saber)."""
    if url in _LIGAS:
        return _LIGAS[url]
    res = None
    for metodo in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=metodo, headers={"User-Agent": "Mozilla/5.0 (revision de enlaces)"})
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                res = (True, r.status); break
        except urllib.error.HTTPError as e:
            if metodo == "HEAD":
                continue
            res = (False, e.code) if e.code in (404, 410) or e.code >= 500 else (None, e.code)
        except urllib.error.URLError as e:
            motivo = str(e.reason)
            res = (False, "el dominio no existe") if "nodename" in motivo or "Name or service" in motivo \
                or "getaddrinfo" in motivo else (None, motivo[:60])
            break
        except Exception as e:   # tiempo agotado, SSL raro…
            res = (None, type(e).__name__)
            break
    _LIGAS[url] = res or (None, "?")
    return _LIGAS[url]


def normaliza(t):
    t = RE_URL.sub("", (t or "").lower())
    t = RE_HASHTAG.sub("", t)
    return re.sub(r"[\W_]+", "", t)[:160]


def textos_recientes(g, excluir=None):
    """{id: texto normalizado} de lo publicado en 30 días y lo programado a 60 (para avisar de repetidos)."""
    hoy = _hoy(g.c.get("zona"))
    out = {}
    for est, d0, d1 in (("published", hoy - dt.timedelta(days=30), hoy), ("scheduled", hoy, hoy + dt.timedelta(days=60))):
        try:
            for p in posts_en(g, est, d0, d1, maximo=300):
                if p.get("_id") != excluir and p.get("parentPostId") != excluir and normaliza(p.get("summary")):
                    out[p.get("_id")] = normaliza(p.get("summary"))
        except Alto:
            pass
    return out


def _vence(x):
    try:
        return dt.datetime.fromisoformat(str(x.get("expire")).replace("Z", "+00:00"))
    except ValueError:
        return None


def revisar_post(cuentas, texto_post, media, formato, cuando=None, ficha=None, recientes=None, ligas=True,
                 primer_comentario=None, zona=None):
    """Revisión antes de programar. cuentas: redes destino (dicts de «redes cuentas»). media: rutas o URLs.
    cuando: datetime con zona (None = borrador). Devuelve [(nivel, texto)]: 🔴 frena · 🟡 conviene revisar."""
    out = []
    t = texto_post or ""
    redes = [x.get("platform") for x in cuentas]
    ahora = dt.datetime.now(dt.timezone.utc)
    # conexiones
    for x in cuentas:
        exp = _vence(x)
        if x.get("isExpired") or (exp and exp < ahora):
            out.append(("🔴", f"{x.get('platform')} ({x.get('name')}) está desconectada: el post va a fallar. Reconéctala en Social Planner."))
        elif exp and cuando and exp < cuando:
            out.append(("🔴", f"La conexión de {x.get('platform')} vence el {exp.astimezone(_tz(zona)):%d-%m %H:%M}, antes de "
                              f"que salga el post ({cuando:%d-%m %H:%M}): va a fallar. Reconéctala antes."))
        elif exp and exp < ahora + dt.timedelta(days=7):
            out.append(("🟡", f"La conexión de {x.get('platform')} vence el {exp.astimezone(_tz(zona)):%d-%m}. Reconéctala pronto."))
    # texto
    if RE_RELLENO.search(t) or (primer_comentario and RE_RELLENO.search(primer_comentario)):
        out.append(("🔴", f"El texto tiene un relleno sin completar: «{(RE_RELLENO.search(t) or RE_RELLENO.search(primer_comentario)).group(0)}»."))
    for r in set(redes):
        lim = LIMITE_TEXTO.get(r)
        if lim and len(t) > lim:
            out.append(("🔴", f"{r} admite {lim} caracteres y el texto tiene {len(t)}: se corta o falla."))
    n_tags = len(RE_HASHTAG.findall(t))
    if "instagram" in redes and n_tags > 30:
        out.append(("🔴", f"Instagram rechaza más de 30 hashtags (trae {n_tags})."))
    if "linkedin" in redes and n_tags > 5:
        out.append(("🟡", f"{n_tags} hashtags en LinkedIn: ahí funcionan mejor 3 a 5."))
    if "instagram" in redes and RE_URL.search(t):
        out.append(("🟡", "En Instagram las ligas del texto no se pueden tocar: usa «liga en la bio» o el primer comentario."))
    if "google" in redes and any(len(re.sub(r"\D", "", x)) >= 10 and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x.strip())
                                 for x in RE_TELEFONO.findall(t)):
        out.append(("🟡", "Google Business suele rechazar publicaciones con número de teléfono en el texto."))
    if primer_comentario and any(r in ("tiktok", "google") for r in redes):
        out.append(("🟡", "TikTok y Google no admiten primer comentario: ahí se ignora."))
    if ficha:
        tl = t.lower()
        for w in ficha.get("prohibidas") or []:
            if re.search(r"(?<!\w)" + re.escape(w.lower()) + r"(?!\w)", tl):
                out.append(("🔴", f"Trae una palabra prohibida en la ficha del cliente: «{w}»."))
        faltan = [h for h in ficha.get("hashtags") or [] if "#" + h not in tl]
        if t and faltan and formato != "story":
            out.append(("🟡", "No trae los hashtags fijos de la ficha: " + " ".join("#" + h for h in faltan)))
    if recientes and normaliza(t) and len(normaliza(t)) >= 25:
        n = normaliza(t)
        if any(n[:120] == x[:120] for x in recientes.values()):
            out.append(("🟡", "El texto es casi igual a otra publicación de los últimos 30 días o ya programada."))
    if cuando and (cuando.hour >= 23 or cuando.hour < 7):
        out.append(("🟡", f"Sale a las {cuando:%H:%M}: de madrugada casi nadie lo ve."))
    # medios
    media = [m for m in (media or []) if m]
    es_video = [bool(re.search(r"\.(mp4|mov|m4v|webm|avi|mkv)(\?|$)", m, re.I)) for m in media]
    for r in set(redes):
        if r in NECESITA_MEDIA and not media:
            out.append(("🔴", f"{r} no admite publicaciones de solo texto: falta imagen o video."))
        if r == "youtube" and media and not any(es_video):
            out.append(("🔴", "YouTube necesita un video."))
        mx = MAX_MEDIA.get(r)
        if mx and len(media) > mx:
            out.append(("🔴" if r != "google" else "🟡",
                        f"{r} admite {mx} archivo(s) por publicación y van {len(media)}" + (": solo usa el primero." if r == "google" else ".")))
    if formato == "reel" and not any(es_video):
        out.append(("🔴", "Un reel necesita un video."))
    if formato == "story" and len(media) > 1:
        out.append(("🟡", f"Van {len(media)} archivos en una historia: cada uno sale como historia aparte."))
    if any(es_video) and not all(es_video) and "tiktok" in redes:
        out.append(("🟡", "TikTok no mezcla fotos y video en la misma publicación."))
    for m, v in zip(media, es_video):
        if m.startswith("http") or not os.path.exists(m):
            continue
        nombre = os.path.basename(m)
        mb = os.path.getsize(m) / 1e6
        if v:
            if mb > 500:
                out.append(("🔴", f"{nombre} pesa {mb:.0f} MB: pasa de los 500 MB que acepta la biblioteca de medios de GHL; comprímelo."))
            elif mb > 300:
                out.append(("🟡", f"{nombre} pesa {mb:.0f} MB: puede tardar o fallar; conviene comprimirlo."))
            info = datos_video(m)
            if info and info.get("ancho") and info.get("alto"):
                ratio = info["ancho"] / info["alto"]
                if formato in ("reel", "story") and not 0.5 <= ratio <= 0.6:
                    out.append(("🟡", f"{nombre} no es vertical 9:16 ({info['ancho']}×{info['alto']}): en {formato} queda con bordes o recortado."))
                s = info.get("segundos") or 0
                if formato == "story" and s > 60:
                    out.append(("🟡", f"{nombre} dura {s:.0f} s: las historias se cortan a 60 s."))
                if formato == "reel" and s > 180:
                    out.append(("🟡", f"{nombre} dura {s:.0f} s: los reels de Instagram admiten hasta 3 min."))
                if "tiktok" in redes and s > 600:
                    out.append(("🟡", f"{nombre} dura {s:.0f} s: TikTok por API admite hasta 10 min."))
        else:
            if mb > 8 and "instagram" in redes:
                out.append(("🟡", f"{nombre} pesa {mb:.1f} MB: Instagram acepta imágenes de hasta 8 MB."))
            dims = medidas_imagen(m)
            if dims and all(dims):
                w, h = dims
                ratio = w / h
                if min(w, h) < 600:
                    out.append(("🟡", f"{nombre} mide {w}×{h}: se va a ver borrosa (mínimo recomendable 1080 px de ancho)."))
                if formato in ("reel", "story") and not 0.5 <= ratio <= 0.6:
                    out.append(("🟡", f"{nombre} no es vertical 9:16 ({w}×{h})."))
                elif formato == "post" and "instagram" in redes and not 0.79 <= ratio <= 1.92:
                    out.append(("🟡", f"{nombre} mide {w}×{h}: Instagram la recorta (admite de 4:5 vertical a 1.91:1 horizontal)."))
    # ligas
    if ligas:
        for u in list(dict.fromkeys(RE_URL.findall(t + " " + (primer_comentario or ""))))[:10]:
            u = u.rstrip(".,;:!?")
            ok, st = liga_viva(u)
            if ok is False:
                out.append(("🔴", f"Liga rota ({st}): {u}"))
            elif ok is None:
                out.append(("🟡", f"No pude comprobar la liga ({st}): {u}. Ábrela a mano."))
    return out


def imprimir_revision(rev, titulo="REVISIÓN"):
    orden = {"🔴": 0, "🟡": 1}
    if not rev:
        print(f"{titulo}: 🟢 sin problemas."); return
    print(f"{titulo}:")
    for nivel, t in sorted(rev, key=lambda x: orden.get(x[0], 2)):
        print(f"  {nivel} {t}")


def revisar_programados(g, dias=14, ligas=True, ficha=None):
    """[(post, revisión)] de lo programado en los próximos días."""
    zona = g.c.get("zona")
    hoy = _hoy(zona)
    accs = {x["id"]: x for x in cuentas_sociales(g)}
    prog = posts_en(g, "scheduled", hoy, hoy + dt.timedelta(days=dias - 1))
    vistos, out = set(), []
    todos = {p.get("_id"): normaliza(p.get("summary")) for p in prog if normaliza(p.get("summary"))}
    for p in prog:
        clave = p.get("parentPostId") or p.get("_id")
        if clave in vistos:
            continue
        vistos.add(clave)
        cuentas = [accs[i] for i in p.get("accountIds") or [] if i in accs]
        rev = []
        if len(cuentas) < len(p.get("accountIds") or []):
            rev.append(("🔴", "Una de sus redes ya no está conectada a la subcuenta: ahí va a fallar."))
        grupo = {x.get("_id") for x in prog if (x.get("parentPostId") or x.get("_id")) == clave} | {clave}
        otros = {k: v for k, v in todos.items() if k not in grupo}
        rev += revisar_post(cuentas, p.get("summary"), [m.get("url") for m in p.get("media") or [] if m.get("url")],
                            p.get("type") or "post", fecha_local(p, zona), ficha, otros, ligas,
                            p.get("followUpComment"), zona)
        out.append((p, rev))
    return out


# ───────────────────────────── CRM: de anuncio a venta y atención ─────────────────────────────
RE_ETQ_ANUNCIO = re.compile(r"(^|[^a-z0-9])(ads?|anuncios?|pauta|paid|cpc|ppc|leadgen|lead-?form)([^a-z0-9]|$)", re.I)
UTM_PAGADO = {"cpc", "ppc", "paid", "paid_social", "paidsocial", "paid-social", "cpm", "ads", "ad", "paid_search", "paid-search"}
RE_VENTA = re.compile(r"ganad|\bclientes?\b|vendid|venta cerrada|cerrad[oa]|pagad|compr[oó]\b", re.I)
RE_VENTA_SUAVE = re.compile(r"✅|🏆|realizad|complet|entregad[oa]\b(?! a)", re.I)
RE_PERDIDA = re.compile(r"perdid|no califica|descart|no asisti|no por ahora|cancelad|✕|❌|🔴", re.I)
RE_CIERRE = re.compile(r"^\W*(ok[a-z]*|va|vale|sale|listo|perfecto|excelente|genial|gracias|muchas gracias|mil gracias|"
                       r"de nada|igualmente|saludos|bye|adi[oó]s|buen d[ií]a|buenas noches|nos vemos|hasta luego|👍|🙏|👌|❤️|😊|🙌)"
                       r"[\W\s]*(gracias)?[\W\s]*$", re.I)
CANALES = {"TYPE_SMS": "SMS", "TYPE_CUSTOM_SMS": "WhatsApp/SMS", "TYPE_WHATSAPP": "WhatsApp", "TYPE_FACEBOOK": "Messenger",
           "TYPE_INSTAGRAM": "Instagram", "TYPE_EMAIL": "correo", "TYPE_GMB": "Google", "TYPE_LIVE_CHAT": "chat web",
           "TYPE_WEBCHAT": "chat web", "TYPE_TIKTOK": "TikTok", "TYPE_CALL": "llamada", "TYPE_CUSTOM_EMAIL": "correo"}


def origen(c, etiquetas=None):
    """'anuncios' · 'redes' · 'otro'. c = contacto, o {'tags','attributions'} de una oportunidad."""
    tags = [str(t).lower() for t in (c.get("tags") or [])]
    if etiquetas:
        if any(e.lower() in t for t in tags for e in etiquetas):
            return "anuncios"
    elif any(RE_ETQ_ANUNCIO.search(t) for t in tags):
        return "anuncios"
    srcs = [c.get("attributionSource") or {}, c.get("lastAttributionSource") or {}] + list(c.get("attributions") or [])
    for s in srcs:
        if any(s.get(k) for k in ("adId", "adSetId", "adsetId", "adName", "fbclid", "gclid", "fbc", "adSource")):
            return "anuncios"
        if str(s.get("utmMedium") or "").lower() in UTM_PAGADO or str(s.get("medium") or "").lower() in UTM_PAGADO:
            return "anuncios"
    for s in srcs:
        m = " ".join(str(s.get(k) or "") for k in ("medium", "sessionSource", "utmSessionSource", "utmSource")).lower()
        if re.search(r"facebook|instagram|social|tiktok|linkedin", m):
            return "redes"
    return "otro"


def contactos_en(g, desde, hasta, maximo=10000):
    """Contactos creados en el rango. Solo se guardan id, etiquetas y origen: nada de nombres ni teléfonos."""
    zona = g.c.get("zona")
    f = [{"field": "dateAdded", "operator": "range",
          "value": {"gte": dia_utc(desde.isoformat(), zona), "lte": dia_utc(hasta.isoformat(), zona, fin=True)}}]
    out, page, total = [], 1, 0
    while len(out) < maximo:
        s, r = g.call("POST", "/contacts/search", body={"locationId": g.loc, "pageLimit": 500, "page": page, "filters": f})
        if s not in (200, 201):
            raise Alto(explica(s, r, "contacts/search"))
        lote = r.get("contacts") or []
        total = r.get("total") or total
        out += [{"id": c.get("id"), "tags": c.get("tags"), "attributionSource": c.get("attributionSource"),
                 "lastAttributionSource": c.get("lastAttributionSource")} for c in lote]
        if len(lote) < 500 or (total and len(out) >= total):
            break
        page += 1
    return out, max(total, len(out))


def pipelines(g):
    r = g.ok("GET", "/opportunities/pipelines", params={"locationId": g.loc})
    return r.get("pipelines") or []


def oportunidades(g, desde, hasta, maximo=5000):
    """Oportunidades creadas entre desde y hasta (fechas date). Sin nombres."""
    out = []
    p = {"location_id": g.loc, "limit": 100, "date": desde.strftime("%m-%d-%Y"), "endDate": hasta.strftime("%m-%d-%Y")}
    while len(out) < maximo:
        s, r = g.call("GET", "/opportunities/search", params=p)
        if s != 200:
            raise Alto(explica(s, r, "opportunities/search"))
        lote = r.get("opportunities") or []
        out += [{"id": o.get("id"), "status": o.get("status"), "pipelineId": o.get("pipelineId"),
                 "pipelineStageId": o.get("pipelineStageId"), "valor": float(o.get("monetaryValue") or 0),
                 "createdAt": o.get("createdAt"), "lastStageChangeAt": o.get("lastStageChangeAt"),
                 "lastStatusChangeAt": o.get("lastStatusChangeAt"), "updatedAt": o.get("updatedAt"),
                 "tags": (o.get("contact") or {}).get("tags"), "attributions": o.get("attributions")} for o in lote]
        m = r.get("meta") or {}
        if len(lote) < 100 or not m.get("startAfterId"):
            break
        p = {**p, "startAfter": m.get("startAfter"), "startAfterId": m.get("startAfterId")}
    return out


def etapas_de_venta(pls, metas):
    """{pipelineId: {stageId: 'venta'|'perdida'|''}} y la explicación de qué se contó como venta."""
    cfg = [x.lower() for x in metas.get("etapas_venta") or []]
    tipo, nombres = {}, []
    for p in pls:
        st = p.get("stages") or []
        t = {}
        for s in st:
            n = s.get("name") or ""
            if cfg:
                t[s["id"]] = "venta" if any(c in n.lower() for c in cfg) else ("perdida" if RE_PERDIDA.search(n) else "")
            else:
                t[s["id"]] = "perdida" if RE_PERDIDA.search(n) else ("venta" if RE_VENTA.search(n) else "")
        if not cfg and "venta" not in t.values():
            for s in st:
                if t[s["id"]] == "" and RE_VENTA_SUAVE.search(s.get("name") or ""):
                    t[s["id"]] = "venta"
        tipo[p["id"]] = t
        nombres += [f"«{s.get('name')}»" for s in st if t[s["id"]] == "venta"]
    return tipo, nombres


def _iso_fecha(x, zona):
    try:
        if isinstance(x, (int, float)):
            return dt.datetime.fromtimestamp(x / 1000, dt.timezone.utc).astimezone(_tz(zona)).date()
        return dt.datetime.fromisoformat(str(x).replace("Z", "+00:00")).astimezone(_tz(zona)).date()
    except (ValueError, OSError, OverflowError):
        return None


def datos_embudo(g, desde, hasta, metas=None, gasto=None, anterior=True):
    """Leads del CRM → oportunidades → ventas, con su origen (anuncios, redes, otro)."""
    metas = metas or {}
    zona = g.c.get("zona")
    etq = metas.get("etiquetas_anuncio")
    cont, total = contactos_en(g, desde, hasta)
    orig = {"anuncios": 0, "redes": 0, "otro": 0}
    for c in cont:
        orig[origen(c, etq)] += 1
    d = {"leads": total, "leads_leidos": len(cont), "origen": orig, "gasto": gasto}
    if anterior:
        d0, h0 = periodo_anterior(desde, hasta)
        c0, t0 = contactos_en(g, d0, h0)
        d["leads_ant"] = t0
        d["leads_anuncio_ant"] = sum(origen(c, etq) == "anuncios" for c in c0)
    pls = pipelines(g)
    tipos, nombres_venta = etapas_de_venta(pls, metas)
    d["cuenta_como_venta"] = nombres_venta
    etapa_nom = {s["id"]: (p.get("name"), s.get("name"), i) for p in pls for i, s in enumerate(p.get("stages") or [])}
    ops = oportunidades(g, desde - dt.timedelta(days=365), hasta)

    def es_venta(o):
        if o["status"] == "won":
            return True
        if o["status"] in ("lost", "abandoned"):
            return False
        return tipos.get(o["pipelineId"], {}).get(o["pipelineStageId"]) == "venta"

    def fecha_venta(o):
        return _iso_fecha(o["lastStatusChangeAt"] if o["status"] == "won" else (o["lastStageChangeAt"] or o["updatedAt"]), zona)

    def en(f, a_, b_):
        return f is not None and a_ <= f <= b_
    nuevas = [o for o in ops if en(_iso_fecha(o["createdAt"], zona), desde, hasta)]
    ventas = [o for o in ops if es_venta(o) and en(fecha_venta(o), desde, hasta)]
    d0, h0 = periodo_anterior(desde, hasta)
    ventas0 = [o for o in ops if es_venta(o) and en(fecha_venta(o), d0, h0)]
    # embudo principal: el configurado o el que más oportunidades nuevas tiene
    pipe = None
    if metas.get("pipeline"):
        q = metas["pipeline"].lower()
        pipe = next((p for p in pls if p["id"] == metas["pipeline"] or q in (p.get("name") or "").lower()), None)
    if not pipe and pls:
        cuenta = {}
        for o in nuevas or ops:
            cuenta[o["pipelineId"]] = cuenta.get(o["pipelineId"], 0) + 1
        pipe = max(pls, key=lambda p: cuenta.get(p["id"], 0))
    etapas = []
    if pipe:
        for s in pipe.get("stages") or []:
            etapas.append((s.get("name"), sum(1 for o in nuevas if o["pipelineStageId"] == s["id"])))
    va = [o for o in ventas if origen(o, etq) == "anuncios"]
    d.update({"oportunidades": len(nuevas), "embudo": pipe.get("name") if pipe else None, "etapas": etapas,
              "ventas": len(ventas), "ventas_ant": len(ventas0), "valor": sum(o["valor"] for o in ventas),
              "ventas_anuncio": len(va), "valor_anuncio": sum(o["valor"] for o in va),
              "valor_ant": sum(o["valor"] for o in ventas0)})
    return d


def liga_chat(g, cid):
    panel = (leer_perfil().get("panel") or "https://app.gohighlevel.com").rstrip("/")
    return f"{panel}/v2/location/{g.loc}/conversations/conversations/{cid}"


def conversaciones_recientes(g, desde_ms, maximo=2000):
    out, ids, p = [], set(), {"locationId": g.loc, "limit": 100, "sort": "desc", "sortBy": "last_message_date"}
    while len(out) < maximo:
        s, r = g.call("GET", "/conversations/search", params=p)
        if s != 200:
            raise Alto(explica(s, r, "conversations/search"))
        lote = r.get("conversations") or []
        nuevos = [c for c in lote if c.get("id") not in ids]
        if not nuevos:
            break
        ids.update(c.get("id") for c in nuevos)
        out += nuevos
        if len(lote) < 100 or (lote[-1].get("lastMessageDate") or 0) < desde_ms:
            break
        p = {**p, "startAfterDate": lote[-1].get("lastMessageDate")}
    return [c for c in out if (c.get("lastMessageDate") or 0) >= desde_ms]


def tiempos_respuesta(g, convs, desde_ms):
    """Horas entre un mensaje del cliente y la siguiente respuesta (de una persona o de un bot)."""
    horas = []
    for c in convs:
        s, r = g.call("GET", f"/conversations/{c['id']}/messages", params={"limit": 100})
        if s != 200:
            continue
        msgs = [m for m in ((r.get("messages") or {}).get("messages") or [])
                if not str(m.get("messageType") or "").startswith("TYPE_ACTIVITY") and m.get("dateAdded")]
        msgs.sort(key=lambda m: m["dateAdded"])
        espera = None
        for m in msgs:
            try:
                t = dt.datetime.fromisoformat(m["dateAdded"].replace("Z", "+00:00"))
            except ValueError:
                continue
            if m.get("direction") == "inbound":
                if espera is None and t.timestamp() * 1000 >= desde_ms:
                    espera = t
            elif m.get("direction") == "outbound" and espera is not None:
                horas.append((t - espera).total_seconds() / 3600)
                espera = None
    return horas


def datos_atencion(g, horas=2, dias=7, muestra=0):
    ahora = dt.datetime.now(dt.timezone.utc).timestamp() * 1000
    desde_ms = ahora - dias * 86400000
    convs = conversaciones_recientes(g, desde_ms)
    pend, cierres = [], 0
    for c in convs:
        if c.get("lastMessageDirection") != "inbound" or c.get("isLastMessageInternalComment"):
            continue
        tipo = str(c.get("lastMessageType") or "")
        if tipo.startswith("TYPE_ACTIVITY"):
            continue
        edad = (ahora - (c.get("lastMessageDate") or ahora)) / 3.6e6
        if edad < horas:
            continue
        if RE_CIERRE.match((c.get("lastMessageBody") or "").strip()[:40]) and (c.get("lastMessageBody") or "").strip():
            cierres += 1
            continue
        pend.append({"id": c.get("id"), "horas": round(edad, 1), "canal": CANALES.get(tipo, tipo.replace("TYPE_", "").lower()),
                     "no_leidos": c.get("unreadCount") or 0, "liga": liga_chat(g, c.get("id"))})
    d = {"conversaciones": len(convs), "sin_respuesta": sorted(pend, key=lambda x: -x["horas"]), "cierres": cierres,
         "no_leidas": sum(1 for c in convs if (c.get("unreadCount") or 0) > 0), "horas": horas, "dias": dias}
    if muestra:
        con_entrada = [c for c in convs if c.get("lastMessageDirection")]
        hs = sorted(tiempos_respuesta(g, con_entrada[:muestra], desde_ms))
        if hs:
            d["tiempos"] = {"n": len(hs), "chats": min(muestra, len(con_entrada)), "mediana": hs[len(hs) // 2],
                            "p90": hs[min(len(hs) - 1, int(len(hs) * 0.9))],
                            "dentro": sum(h <= horas for h in hs) / len(hs) * 100}
    return d


def crm_seguro(fn):
    """Lo del CRM no tumba el resto: sin permisos o con error, devuelve {'sin_crm': motivo}."""
    try:
        return fn()
    except Alto as e:
        m = str(e)
        if "scope" in m.lower() or "HTTP 401" in m:
            return {"sin_crm": "el PIT no trae los permisos del CRM (contactos, oportunidades, conversaciones: docs/PIT.md)"}
        return {"sin_crm": m.split("\n")[0][:140]}
    except Exception as e:   # datos raros de la API: que no tumbe el resto
        return {"sin_crm": f"fallo inesperado leyendo el CRM ({type(e).__name__}: {str(e)[:100]})"}


def duracion(h):
    if h < 1:
        return f"{max(h * 60, 0):.0f} min"
    if h < 48:
        return f"{h:.1f} h".replace(".0 h", " h")
    return f"{h / 24:.0f} días"


def lineas_embudo(e, pais):
    """Texto del embudo para la terminal."""
    o = e["origen"]
    L = [f"Leads nuevos        {num(e['leads'], pais)}  ({delta(e['leads'], e.get('leads_ant'))} vs. periodo anterior) · "
         f"de anuncios {num(o['anuncios'], pais)} · redes {num(o['redes'], pais)} · otro origen {num(o['otro'], pais)}"]
    if e.get("leads_leidos", e["leads"]) < e["leads"]:
        L.append(f"   (el origen se calculó con los primeros {num(e['leads_leidos'], pais)})")
    g_ = e.get("gasto")
    if g_:
        L.append(f"Costo por lead de anuncios  {dinero(g_ / o['anuncios'], pais) if o['anuncios'] else '— (ningún lead marcado como de anuncios)'}"
                 f"  · inversión {dinero(g_, pais)}")
    L.append(f"Oportunidades nuevas {num(e['oportunidades'], pais)}" + (f" · embudo «{e['embudo']}»" if e.get("embudo") else ""))
    if e["etapas"] and e["oportunidades"]:
        L.append("   dónde están hoy: " + " → ".join(f"{n} {c}" for n, c in e["etapas"]))
    L.append(f"Ventas              {num(e['ventas'], pais)} ({delta(e['ventas'], e['ventas_ant'])}) · valor {dinero(e['valor'], pais)} · "
             f"de anuncios {num(e['ventas_anuncio'], pais)} ({dinero(e['valor_anuncio'], pais)})")
    if g_:
        cpv = dinero(g_ / e["ventas_anuncio"], pais) if e["ventas_anuncio"] else "—"
        roas = f"{e['valor_anuncio'] / g_:.1f}×" if e["valor_anuncio"] else "—"
        L.append(f"Costo por venta de anuncios {cpv} · retorno (valor vendido ÷ inversión) {roas}")
    if e["leads"]:
        L.append(f"De lead a venta     {e['ventas'] / e['leads'] * 100:.1f} %")
    L.append("Cuenta como venta: " + (", ".join(e["cuenta_como_venta"]) or "solo las marcadas como ganadas (won)")
             + "  → cámbialo con: metas --etapas-venta \"…\"")
    return L


def cmd_crm(a):
    g = Ghl(cuenta_activa(a.cuenta)); zona, pais = g.c.get("zona"), g.c.get("pais")
    metas = leer_metas(g.c["alias"])
    if a.accion == "etapas":
        pls = pipelines(g)
        tipos, _ = etapas_de_venta(pls, metas)
        for p in pls:
            print(f"■ {p.get('name')}  id={p['id']}")
            for s in p.get("stages") or []:
                t = tipos[p["id"]].get(s["id"])
                print(f"   {'💰 venta  ' if t == 'venta' else ('✖ perdida ' if t == 'perdida' else '          ')} {s.get('name')}")
        print("\n💰 = cuenta como venta. Para cambiarlo: python3 ghl.py metas --etapas-venta \"Cita agendada,Cliente\"")
        return
    if a.accion == "embudo":
        desde, hasta = rango_fechas(a, zona, por_defecto=30)
        print(f"Calculando el embudo de «{g.c.get('nombre')}» {desde} → {hasta}…", file=sys.stderr)
        ads = datos_ads(g, desde, hasta)
        gasto = None if "sin_ads" in ads else ads["actual"]["spend"]
        e = datos_embudo(g, desde, hasta, metas, gasto)
        if a.json:
            jprint({k: v for k, v in e.items()}); return
        print(f"Embudo de «{g.c.get('nombre')}» · {desde} → {hasta}\n")
        for l in lineas_embudo(e, pais):
            print("  " + l)
        if "sin_ads" in ads:
            print(f"\n  (sin datos de anuncios: {ads['sin_ads']})")
        if gasto and not e["origen"]["anuncios"]:
            print("\n  ⚠️ Hubo inversión, pero ningún lead quedó marcado como de anuncios. Dime qué etiqueta les pone el CRM: "
                  "metas --etiquetas-anuncio \"fb-ad,meta-lead\"")
        return
    if a.accion == "atencion":
        horas = a.horas or metas.get("responder_horas") or 2
        dias = a.dias or 7
        print("Leyendo conversaciones…", file=sys.stderr)
        d = datos_atencion(g, horas, dias, muestra=a.muestra)
        if a.json:
            jprint(d); return
        print(f"Atención de «{g.c.get('nombre')}» · últimos {dias} días · {num(d['conversaciones'], pais)} conversaciones con movimiento\n")
        p = d["sin_respuesta"]
        if p:
            print(f"  {'🔴' if len(p) >= 5 or p[0]['horas'] > 24 else '🟡'} {len(p)} conversación(es) esperan respuesta hace más de "
                  f"{duracion(horas)} (la más vieja: {duracion(p[0]['horas'])})")
            for x in p[:None if a.todas else 15]:
                print(f"     · {duracion(x['horas']):>8} · {x['canal']:<12} {x['liga']}")
            if len(p) > 15 and not a.todas:
                print(f"     … y {len(p) - 15} más (--todas)")
        else:
            print(f"  🟢 Nadie espera respuesta hace más de {duracion(horas)}.")
        if d["cierres"]:
            print(f"  ℹ️  {d['cierres']} terminan en «gracias», «ok» o parecido y no se cuentan como pendientes.")
        print(f"  No leídas: {d['no_leidas']}")
        t = d.get("tiempos")
        if t:
            print(f"  Tiempo de respuesta ({t['chats']} chats, {t['n']} respuestas): mediana {duracion(t['mediana'])} · "
                  f"9 de cada 10 en menos de {duracion(t['p90'])} · {t['dentro']:.0f} % dentro de {duracion(horas)}. "
                  "Incluye respuestas automáticas (bots).")
        return


def piezas(posts):
    """Cuántas publicaciones distintas hay: el mismo post en FB e IG cuenta una vez."""
    grupos, contenidos, n = set(), set(), 0
    for p in posts:
        f = str(p.get("publishedAt") or p.get("scheduleDate") or p.get("displayDate") or "")[:16]
        g_, c_ = p.get("parentPostId") or p.get("_id"), (normaliza(p.get("summary")), f, p.get("type"))
        if g_ not in grupos and c_ not in contenidos:
            n += 1
        grupos.add(g_); contenidos.add(c_)
    return n


def cumplimiento_metas(g, metas, red=None, ads=None, emb=None, dias=7):
    """[(campo, valor, meta, ok)] para mostrar contra las metas del cliente."""
    out = []
    pais = g.c.get("pais")
    if red is not None and metas.get("posts_semana"):
        n_piezas = piezas(red["posts"])
        ritmo = n_piezas / max(dias / 7, 1 / 7)
        out.append(("Publicaciones por semana", f"{ritmo:.1f}".replace(".0", ""), f"{metas['posts_semana']:g}", ritmo >= metas["posts_semana"] * 0.95))
    if ads and "sin_ads" not in ads and metas.get("costo_max"):
        r_, n = resultado_ads(ads["actual"])
        if ads["actual"]["spend"] and r_:
            c = ads["actual"]["spend"] / r_
            out.append((f"Costo por {SINGULAR[n]}", dinero(c, pais), "máx. " + dinero(metas["costo_max"], pais), c <= metas["costo_max"]))
    if emb and "sin_crm" not in emb:
        f = 30 / max(dias, 1)
        if metas.get("leads_mes"):
            out.append(("Leads (ritmo mensual)", num(emb["leads"] * f, pais), num(metas["leads_mes"], pais), emb["leads"] * f >= metas["leads_mes"] * 0.95))
        if metas.get("ventas_mes"):
            out.append(("Ventas (ritmo mensual)", num(emb["ventas"] * f, pais), num(metas["ventas_mes"], pais), emb["ventas"] * f >= metas["ventas_mes"] * 0.95))
    return out


# ───────────────────────────── AGENCIA: varios clientes a la vez ─────────────────────────────
def _cada_cliente(a, fn):
    resultados = []
    for alias, datos in todas_las_cuentas(a.cuentas):
        g = Ghl({"alias": alias, **datos, "pit": datos.get("pit") or ""})
        try:
            g = Ghl(con_pit(alias, datos))
            resultados.append((alias, g, fn(g)))
        except Alto as e:
            resultados.append((alias, g, {"error": str(e).split("\n")[0][:160]}))
        except Exception as e:   # un cliente con datos raros no tumba a los demás
            resultados.append((alias, g, {"error": f"fallo inesperado ({type(e).__name__}: {str(e)[:110]})"}))
    return resultados


def cmd_agencia(a):
    if a.accion == "resumen":
        def fn(g):
            desde, hasta = rango_fechas(a, g.c.get("zona"))
            red = datos_redes(g, desde, hasta, con_metricas=False)
            d0, h0 = periodo_anterior(desde, hasta)
            pub0 = posts_en(g, "published", d0, h0)
            ads = datos_ads(g, desde, hasta)
            metas = leer_metas(g.c["alias"])
            d = {"rango": (desde, hasta), "red": red, "ads": ads, "metas": metas,
                 "pub0": len(pub0), "int0": sum(interaccion(p) for p in pub0)}
            if not a.sin_crm:
                gasto = None if "sin_ads" in ads else ads["actual"]["spend"]
                d["emb"] = crm_seguro(lambda: datos_embudo(g, desde, hasta, metas, gasto))
                d["atn"] = crm_seguro(lambda: datos_atencion(g, metas.get("responder_horas") or 2, 7))
            return d
        res = _cada_cliente(a, fn)
        if a.json:
            jprint([{"cliente": al, **({"error": d["error"]} if "error" in d else {
                "desde": str(d["rango"][0]), "hasta": str(d["rango"][1]), "publicados": d["red"]["publicados"],
                "interaccion": d["red"]["interaccion"], "fallidos": len(d["red"]["fallidos"]),
                "programados_14d": len(d["red"]["programados"]), "vencidas": d["red"]["vencidas"],
                "ads": d["ads"] if "sin_ads" in d["ads"] else {"actual": d["ads"]["actual"], "anterior": d["ads"]["anterior"]},
                "crm": d.get("emb"), "sin_respuesta": None if not d.get("atn") or "sin_crm" in d["atn"] else len(d["atn"]["sin_respuesta"]),
                "metas": [{"que": q, "valor": v, "meta": m, "ok": ok} for q, v, m, ok in
                          cumplimiento_metas(g, d["metas"], d["red"], d["ads"], d.get("emb"), (d["rango"][1] - d["rango"][0]).days + 1)]})}
                    for al, g, d in res]); return
        for al, g, d in res:
            pais = g.c.get("pais")
            print(f"\n■ {g.c.get('nombre')}  [{al}]")
            if "error" in d:
                print("   ⚠️ ", d["error"]); continue
            r = d["red"]
            print(f"   Periodo {d['rango'][0]} → {d['rango'][1]} (vs. periodo anterior)")
            print(f"   Redes   {r['publicados']} publicados ({delta(r['publicados'], d['pub0'])}) · interacción {r['interaccion']} "
                  f"({delta(r['interaccion'], d['int0'])}) · {len(r['fallidos'])} fallidos · {len(r['programados'])} programados (14 días)"
                  + (f" · 🔴 vencidas: {', '.join(r['vencidas'])}" if r['vencidas'] else ""))
            ad = d["ads"]
            if "sin_ads" in ad:
                print(f"   Anuncios — ({ad['sin_ads']})")
            else:
                x, y = ad["actual"], ad["anterior"]
                rx, n = resultado_ads(x); ry, _ = resultado_ads(y)
                cpr = dinero(x["spend"] / rx, pais) if rx else "—"
                print(f"   Anuncios gasto {dinero(x['spend'], pais)} ({delta(x['spend'], y['spend'])}) · {num(rx, pais)} {n} "
                      f"({delta(rx, ry)}) · costo c/u {cpr} · CTR {x['ctr']:.2f}% · frec. {x['frequency']:.1f}")
            e, at = d.get("emb"), d.get("atn")
            if e is not None:
                if "sin_crm" in e:
                    print(f"   CRM     — ({e['sin_crm']})")
                else:
                    o, gs = e["origen"], e.get("gasto")
                    cpl = f" · costo por lead {dinero(gs / o['anuncios'], pais)}" if gs and o["anuncios"] else ""
                    cpv = f" · costo por venta {dinero(gs / e['ventas_anuncio'], pais)}" if gs and e["ventas_anuncio"] else ""
                    sr = f" · {len(at['sin_respuesta'])} chats sin respuesta" if at and "sin_crm" not in at and at["sin_respuesta"] else ""
                    print(f"   CRM     {num(e['leads'], pais)} leads ({delta(e['leads'], e.get('leads_ant'))}; {num(o['anuncios'], pais)} de anuncios)"
                          f"{cpl} · {num(e['ventas'], pais)} ventas ({dinero(e['valor'], pais)}){cpv}{sr}")
            cm = cumplimiento_metas(g, d["metas"], r, d["ads"], e, (d["rango"][1] - d["rango"][0]).days + 1)
            if cm:
                print("   Metas   " + " · ".join(f"{q} {v} de {m} {'✓' if ok else '✗'}" for q, v, m, ok in cm))
        return
    if a.accion == "alertas":
        def fn(g):
            desde, hasta = rango_fechas(a, g.c.get("zona"))
            red = datos_redes(g, desde, hasta, con_metricas=False)
            ads = datos_ads(g, desde, hasta)
            metas = leer_metas(g.c["alias"])
            hoy = _hoy(g.c.get("zona"))
            ini_mes, ayer = hoy.replace(day=1), hoy - dt.timedelta(days=1)
            ads_mes = None
            if metas.get("gasto_mes") and "sin_ads" not in ads and hoy.day > 1:
                s, r = g.call("GET", f"{ADP}/reporting", params={"locationId": g.loc, "type": "INTEGRATION",
                                                                 "startDate": ini_mes.isoformat(), "endDate": ayer.isoformat(),
                                                                 "fields": FIELDS}, version=V_ADS)
                if s == 200:
                    gr = r.get("grouped") or []
                    ads_mes = _fila(gr[0] if gr else r.get("totals"))["spend"]
            atn = emb = None
            if not a.sin_crm:
                atn = crm_seguro(lambda: datos_atencion(g, metas.get("responder_horas") or 2, 7))
                if (metas.get("leads_mes") or metas.get("ventas_mes")) and hoy.day > 1:
                    emb = crm_seguro(lambda: datos_embudo(g, ini_mes, ayer, metas, None, anterior=False))
            al = alertas_de(g, red, ads, metas, atn, emb, ads_mes, (hasta - desde).days + 1)
            if atn and "sin_crm" in atn:
                al.append(("ℹ️", "Sin datos del CRM: " + atn["sin_crm"]))
            return {"alertas": al}
        res = _cada_cliente(a, fn)
        if a.json:
            jprint([{"cliente": al, **d} for al, g, d in res]); return
        total = 0
        for al, g, d in res:
            print(f"\n■ {g.c.get('nombre')}  [{al}]")
            if "error" in d:
                print("   ⚠️ ", d["error"]); continue
            orden = {"🔴": 0, "🟡": 1, "🟢": 2, "ℹ️": 3}
            for nivel, t in sorted(d["alertas"], key=lambda x: orden.get(x[0], 3)):
                print(f"   {nivel} {t}")
                total += nivel in ("🔴", "🟡")
            if not d["alertas"]:
                print("   🟢 Todo en orden.")
        print(f"\n{total} punto(s) para revisar.")
        return
    if a.accion == "calendario":
        dias = a.dias or 14
        filas = []

        def fn(g):
            zona = g.c.get("zona")
            hoy = _hoy(zona)
            prog = posts_en(g, "scheduled", hoy, hoy + dt.timedelta(days=dias - 1))
            borr = posts_en(g, "draft") if a.borradores else []
            return {"hoy": hoy, "prog": prog, "borr": borr}
        res = _cada_cliente(a, fn)
        if a.json:
            jprint([{"cliente": al, **({"error": d["error"]} if "error" in d else {
                "programados": [resumen_post(p) for p in d["prog"]],
                "borradores": [resumen_post(p) for p in d["borr"]]})} for al, g, d in res]); return
        for al, g, d in res:
            print(f"\n■ {g.c.get('nombre')}  [{al}]")
            if "error" in d:
                print("   ⚠️ ", d["error"]); continue
            zona = g.c.get("zona")
            por_dia = {}
            for p in d["prog"]:
                f = fecha_local(p, zona)
                if f: por_dia.setdefault(f.date(), []).append((f, p))
            vacios = []
            for i in range(dias):
                dia = d["hoy"] + dt.timedelta(days=i)
                if dia in por_dia:
                    for f, p in sorted(por_dia[dia], key=lambda x: x[0]):
                        r = resumen_post(p)
                        print(f"   {DIAS_ES[dia.weekday()][:3]} {dia:%d-%m} {f:%H:%M}  {r['red']:<9} {(r['tipo'] or ''):<6} {r['texto'][:60]}")
                else:
                    vacios.append(f"{DIAS_ES[dia.weekday()][:3]} {dia:%d-%m}")
            if not d["prog"]:
                print(f"   (nada programado en {dias} días)")
            elif vacios:
                print(f"   Días sin publicación: {', '.join(vacios)}")
            if a.borradores:
                print(f"   Borradores esperando revisión: {len(d['borr'])}")
                for p in d["borr"][:10]:
                    print(f"     · {resumen_post(p)['texto'][:70]}  [{p.get('_id')}]")
        return


# ───────────────────────────── ANÁLISIS de contenido (un cliente) ─────────────────────────────
def cmd_analisis(a):
    g = Ghl(cuenta_activa(a.cuenta)); zona = g.c.get("zona")
    desde, hasta = rango_fechas(a, zona, por_defecto=90)
    pub = posts_en(g, "published", desde, hasta, maximo=1500)
    if not pub:
        print(f"No hay posts publicados entre {desde} y {hasta}."); return
    filas = []
    for p in pub:
        f = fecha_local(p, zona)
        txt = p.get("summary") or ""
        filas.append({"red": p.get("platform") or "?", "formato": p.get("type") or "post", "int": interaccion(p),
                      "dia": DIAS_ES[f.weekday()] if f else "?", "hora": f.hour if f else None,
                      "largo": "corto (<150)" if len(txt) < 150 else "medio (150-600)" if len(txt) < 600 else "largo (600+)",
                      "pregunta": "con pregunta" if "?" in txt else "sin pregunta",
                      "texto": txt[:70].replace("\n", " "), "liga": p.get("previewLink"), "fecha": f})

    def tabla(titulo, clave, minimo=2):
        g_ = {}
        for x in filas:
            if x[clave] is None: continue
            g_.setdefault(x[clave], []).append(x["int"])
        orden = sorted(((k, sum(v) / len(v), len(v)) for k, v in g_.items() if len(v) >= minimo), key=lambda t: -t[1])
        if a.json:
            return {titulo: [{"grupo": k, "promedio": round(p, 1), "posts": n} for k, p, n in orden]}
        print(f"\n{titulo} (interacción promedio por post · n posts):")
        mx = max([p for _, p, _ in orden] or [1]) or 1
        for k, p, n in orden:
            print(f"   {str(k):<18} {p:6.1f}  {'█' * max(1, int(p / mx * 24))}  ({n})")
        return {}
    print(f"Análisis de {len(filas)} posts publicados · {desde} → {hasta} · «{g.c.get('nombre')}»"
          f"\nInteracción = likes + 2×comentarios + 3×compartidos (lo que GHL mide por post).") if not a.json else None
    out = {}
    out.update(tabla("Por red", "red", 1))
    out.update(tabla("Por formato", "formato", 1))
    out.update(tabla("Por día de la semana", "dia"))
    for x in filas:
        h = x["hora"]
        x["franja"] = None if h is None else ("madrugada 0-7" if h < 8 else "mañana 8-11" if h < 12 else
                                              "mediodía 12-14" if h < 15 else "tarde 15-18" if h < 19 else "noche 19-23")
    out.update(tabla("Por franja horaria", "franja"))
    out.update(tabla("Por largo del texto", "largo"))
    out.update(tabla("Con o sin pregunta", "pregunta"))
    filas.sort(key=lambda x: -x["int"])
    if a.json:
        out["top"] = [{k: v for k, v in x.items() if k != "fecha"} for x in filas[:5]]
        out["peores"] = [{k: v for k, v in x.items() if k != "fecha"} for x in filas[-5:]]
        jprint(out); return
    print("\nLos 5 mejores:")
    for x in filas[:5]:
        print(f"   {x['int']:>4}  {x['fecha'].strftime('%d-%m') if x['fecha'] else '--/--'} {x['red']:<9} {x['formato']:<6} {x['texto'][:55]}  {x['liga'] or ''}")
    print("Los 5 más flojos:")
    for x in filas[-5:]:
        print(f"   {x['int']:>4}  {x['fecha'].strftime('%d-%m') if x['fecha'] else '--/--'} {x['red']:<9} {x['formato']:<6} {x['texto'][:55]}")
    print("\nOjo: grupos con pocos posts no son concluyentes; GHL no da alcance por post, solo interacción.")


# ───────────────────────────── INFORME mensual para el cliente ─────────────────────────────
def cmd_informe(a):
    g = Ghl(cuenta_activa(a.cuenta)); zona, pais = g.c.get("zona"), g.c.get("pais")
    desde, hasta = rango_fechas(a, zona, por_defecto=30)
    d0, h0 = periodo_anterior(desde, hasta)
    print(f"Armando informe de «{g.c.get('nombre')}» {desde} → {hasta}…", file=sys.stderr)
    red = datos_redes(g, desde, hasta)
    pub0 = posts_en(g, "published", d0, h0)
    ads = datos_ads(g, desde, hasta, detalle=True)
    metas = leer_metas(g.c["alias"])
    emb = None if a.sin_crm else crm_seguro(lambda: datos_embudo(
        g, desde, hasta, metas, None if "sin_ads" in ads else ads["actual"]["spend"]))
    al = alertas_de(g, red, ads, metas, emb=emb, dias=(hasta - desde).days + 1)
    L = []
    w = L.append
    w(f"# Informe de marketing · {g.c.get('nombre')}")
    w(f"\n**Periodo:** {desde:%d-%m-%Y} al {hasta:%d-%m-%Y} · comparado con {d0:%d-%m-%Y} al {h0:%d-%m-%Y}\n")
    w("## Resumen\n")
    w("| | Este periodo | Anterior | Cambio |\n|---|---:|---:|---:|")
    def bruta(p):
        i = p.get("insights") or {}
        return _int(i.get("like")) + _int(i.get("comment")) + _int(i.get("share"))
    i1, i0 = sum(bruta(p) for p in red["posts"]), sum(bruta(p) for p in pub0)
    w(f"| Publicaciones | {red['publicados']} | {len(pub0)} | {delta(red['publicados'], len(pub0))} |")
    w(f"| Interacción (likes + comentarios + compartidos) | {num(i1, pais)} | {num(i0, pais)} | {delta(i1, i0)} |")
    if "sin_ads" not in ads:
        x, y = ads["actual"], ads["anterior"]
        rx, n = resultado_ads(x); ry, _ = resultado_ads(y)
        w(f"| Inversión en anuncios | {dinero(x['spend'], pais)} | {dinero(y['spend'], pais)} | {delta(x['spend'], y['spend'])} |")
        w(f"| {n.capitalize()} por anuncios | {num(rx, pais)} | {num(ry, pais)} | {delta(rx, ry)} |")
        w(f"| Costo por {SINGULAR[n]} | {dinero(x['spend']/rx, pais) if rx else '—'} | "
          f"{dinero(y['spend']/ry, pais) if ry else '—'} | {delta(x['spend']/rx if rx else 0, y['spend']/ry if ry else 0)} |")
        w(f"| Personas alcanzadas (anuncios) | {num(x['reach'], pais)} | {num(y['reach'], pais)} | {delta(x['reach'], y['reach'])} |")
    w("\n## Redes sociales\n")
    if red["por_red"]:
        por_red = {}
        for p in red["posts"]:
            x = por_red.setdefault(p.get("platform") or "?", [0, 0]); x[0] += 1; x[1] += bruta(p)
        w("| Red | Publicaciones | Interacción |\n|---|---:|---:|")
        for k, (n_, i_) in sorted(por_red.items(), key=lambda t: -t[1][1]):
            w(f"| {k} | {n_} | {num(i_, pais)} |")
    m7 = red.get("metricas7")
    if m7:
        t, b = m7.get("totals") or {}, m7.get("breakdowns") or {}
        w(f"\n**Últimos 7 días** (GHL solo entrega esta ventana): {num(t.get('impressions'), pais)} impresiones "
          f"({(b.get('impressions') or {}).get('totalChange')}% vs. semana previa), alcance {num((b.get('reach') or {}).get('total'), pais)}, "
          f"{num(t.get('followers'), pais)} seguidores nuevos.")
    top = [p for p in sorted(red["posts"], key=interaccion, reverse=True) if interaccion(p) > 0][:5]
    if red["posts"] and not top:
        w("\nGHL no registró likes, comentarios ni compartidos en las publicaciones del periodo (pasa con las historias, "
          "que no los tienen, o si la conexión de la red no da permiso de estadísticas).")
    if top:
        w("\n### Las publicaciones que mejor funcionaron\n")
        for p in top:
            r = resumen_post(p); f = fecha_local(p, zona)
            liga = f" · [ver]({r['liga']})" if r["liga"] else ""
            w(f"1. **{f.strftime('%d-%m') if f else 's/f'} · {r['red']}** — {r['texto'][:90]} (❤ {r['likes'] or 0} · 💬 {r['comentarios'] or 0} · ↗ {r['compartidos'] or 0}){liga}")
    if red["fallidos"]:
        w(f"\n**Publicaciones que no salieron:** {len(red['fallidos'])}.")
    if "sin_ads" not in ads and ads["campanas"]:
        w("\n## Anuncios\n")
        w("| Campaña | Inversión | Impresiones | Clics | Resultados | Costo c/u |\n|---|---:|---:|---:|---:|---:|")
        for c in ads["campanas"][:8]:
            res = c.get("conversaciones") or c.get("leads") or c.get("clics_enlace") or 0
            w(f"| {c['nombre'][:55]} | {dinero(c['gasto'], pais)} | {num(c['impresiones'], pais)} | {num(c['clics'], pais)} | "
              f"{num(res, pais) if res else '—'} | {dinero(c['gasto']/res, pais) if res else '—'} |")
        mejores = [f for c in ads["campanas"] for f in c.get("conjuntos", []) if resultado_ads(f)[0]]
        if mejores:
            m = min(mejores, key=lambda f: f["spend"] / resultado_ads(f)[0])
            w(f"\nEl público que mejor rindió: **{m['nombre']}** ({dinero(m['spend'] / resultado_ads(m)[0], pais)} por resultado).")
    elif "sin_ads" in ads:
        w(f"\n## Anuncios\n\nSin datos de anuncios en esta subcuenta ({ads['sin_ads']}).")
    if emb and "sin_crm" not in emb:
        o, gs = emb["origen"], emb.get("gasto")
        w("\n## De anuncio a venta\n")
        w("| | Este periodo | Anterior | Cambio |\n|---|---:|---:|---:|")
        w(f"| Contactos nuevos | {num(emb['leads'], pais)} | {num(emb.get('leads_ant'), pais)} | {delta(emb['leads'], emb.get('leads_ant'))} |")
        w(f"| …de anuncios | {num(o['anuncios'], pais)} | {num(emb.get('leads_anuncio_ant'), pais)} | {delta(o['anuncios'], emb.get('leads_anuncio_ant'))} |")
        w(f"| Ventas | {num(emb['ventas'], pais)} | {num(emb['ventas_ant'], pais)} | {delta(emb['ventas'], emb['ventas_ant'])} |")
        w(f"| Valor vendido | {dinero(emb['valor'], pais)} | {dinero(emb['valor_ant'], pais)} | {delta(emb['valor'], emb['valor_ant'])} |")
        if gs:
            w(f"\n- **Costo por contacto de anuncios:** {dinero(gs / o['anuncios'], pais) if o['anuncios'] else '—'}")
            w(f"- **Ventas que vinieron de anuncios:** {num(emb['ventas_anuncio'], pais)} ({dinero(emb['valor_anuncio'], pais)})"
              + (f" · costo por venta {dinero(gs / emb['ventas_anuncio'], pais)}" if emb["ventas_anuncio"] else ""))
            if emb["valor_anuncio"]:
                w(f"- **Retorno:** por cada {dinero(1, pais)} invertido se vendieron {dinero(emb['valor_anuncio'] / gs, pais)}.")
        if emb["etapas"] and emb["oportunidades"]:
            w(f"\n**Oportunidades nuevas: {num(emb['oportunidades'], pais)}**, dónde están hoy: "
              + " · ".join(f"{n} {c}" for n, c in emb["etapas"] if c) + ".")
    cm = cumplimiento_metas(g, metas, red, ads, emb, (hasta - desde).days + 1)
    if cm:
        w("\n## Metas\n")
        w("| | Resultado | Meta | |\n|---|---:|---:|:---:|")
        for q, v, m, ok in cm:
            w(f"| {q} | {v} | {m} | {'✅' if ok else '⚠️'} |")
    w("\n## Para revisar\n")
    for nivel, t in al or [("🟢", "Todo en orden.")]:
        w(f"- {nivel} {t}")
    w("\n## Próximos pasos sugeridos\n")
    sug = []
    if top and red["por_red"]:
        mejor_red = max(red["por_red"].items(), key=lambda t: t[1]["interaccion"] / max(t[1]["posts"], 1))[0]
        sug.append(f"Repetir el estilo de las publicaciones destacadas; {mejor_red} es la red con más interacción por publicación.")
    if not red["programados"]:
        sug.append("Programar la parrilla de las próximas dos semanas.")
    if "sin_ads" not in ads and ads["actual"]["frequency"] > 3:
        sug.append("Renovar los creativos de anuncios (el público ya los vio muchas veces).")
    for x in sug or ["Mantener el ritmo de publicación y revisar resultados la próxima semana."]:
        w(f"- {x}")
    w(f"\n---\n*Datos tomados de GoHighLevel el {_hoy(zona):%d-%m-%Y}. La interacción por publicación incluye likes, "
      "comentarios y compartidos; GHL no entrega el alcance por publicación.*")
    texto_md = "\n".join(L) + "\n"
    salida = a.salida or os.path.join("informes", f"{g.c['alias']}_{desde}_{hasta}.md")
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    with open(salida, "w", encoding="utf-8") as h:
        h.write(texto_md)
    print(texto_md if a.mostrar else "")
    print(f"✅ Informe guardado en {salida}")


# ───────────────────────────── EXPORTAR a CSV ─────────────────────────────
def cmd_exportar(a):
    g = Ghl(cuenta_activa(a.cuenta)); zona = g.c.get("zona")
    desde, hasta = rango_fechas(a, zona, por_defecto=30)
    os.makedirs("exportes", exist_ok=True)
    if a.que == "posts":
        pub = posts_en(g, "published", desde, hasta, maximo=3000)
        salida = a.salida or f"exportes/{g.c['alias']}_posts_{desde}_{hasta}.csv"
        with open(salida, "w", newline="", encoding="utf-8-sig") as h:
            w = csv.writer(h)
            w.writerow(["fecha", "hora", "dia", "red", "formato", "likes", "comentarios", "compartidos", "interaccion", "texto", "liga"])
            for p in pub:
                f = fecha_local(p, zona); i = p.get("insights") or {}
                w.writerow([f"{f:%Y-%m-%d}" if f else "", f"{f:%H:%M}" if f else "", DIAS_ES[f.weekday()] if f else "",
                            p.get("platform"), p.get("type"), _int(i.get("like")), _int(i.get("comment")), _int(i.get("share")),
                            interaccion(p), (p.get("summary") or "").replace("\n", " ")[:500], p.get("previewLink") or ""])
        print(f"✅ {len(pub)} posts → {salida}"); return
    if a.que == "ads-diario":
        salida = a.salida or f"exportes/{g.c['alias']}_ads-diario_{desde}_{hasta}.csv"
        filas, d = [], desde
        while d <= hasta:
            s, r = g.call("GET", f"{ADP}/reporting", params={"locationId": g.loc, "type": "INTEGRATION", "startDate": d.isoformat(),
                                                            "endDate": d.isoformat(), "fields": FIELDS}, version=V_ADS)
            if s != 200:
                die(explica(s, r, "reporting"))
            gr = r.get("grouped") or []
            f = _fila(gr[0] if gr else r.get("totals"))
            filas.append([d.isoformat(), DIAS_ES[d.weekday()], round(f["spend"], 2), int(f["impressions"]), int(f["reach"]),
                          int(f["clicks"]), round(f["ctr"], 2), round(f["cpm"], 2), int(f["conversaciones"]), int(f["leads"]),
                          int(f["clics_enlace"])])
            d += dt.timedelta(days=1)
        with open(salida, "w", newline="", encoding="utf-8-sig") as h:
            w = csv.writer(h)
            w.writerow(["fecha", "dia", "gasto", "impresiones", "alcance", "clics", "ctr", "cpm", "conversaciones", "leads", "clics_enlace"])
            w.writerows(filas)
        print(f"✅ {len(filas)} días → {salida}"); return
    if a.que == "ads-campanas":
        salida = a.salida or f"exportes/{g.c['alias']}_ads-conjuntos_{desde}_{hasta}.csv"
        ads = datos_ads(g, desde, hasta, detalle=True)
        if "sin_ads" in ads:
            die(f"Sin anuncios: {ads['sin_ads']}")
        with open(salida, "w", newline="", encoding="utf-8-sig") as h:
            w = csv.writer(h)
            w.writerow(["campana", "conjunto", "gasto", "impresiones", "alcance", "clics", "ctr", "frecuencia", "conversaciones", "leads", "clics_enlace"])
            for c in ads["campanas"]:
                for f in c.get("conjuntos", []):
                    w.writerow([c["nombre"], f["nombre"], round(f["spend"], 2), int(f["impressions"]), int(f["reach"]), int(f["clicks"]),
                                round(f["ctr"], 2), round(f["frequency"], 2), int(f["conversaciones"]), int(f["leads"]), int(f["clics_enlace"])])
        print(f"✅ → {salida} (las 8 campañas con más gasto)"); return


# ───────────────────────────── PERFIL de quien usa el repo ─────────────────────────────
PERFIL = os.path.join(DIR, "perfil.json")


def cmd_perfil(a):
    p = {}
    if os.path.exists(PERFIL):
        with open(PERFIL, encoding="utf-8") as h:
            p = json.load(h)
    cambios = {k: v for k, v in {"nombre": a.nombre, "agencia": a.agencia, "pais": a.pais, "tono": a.tono,
                                 "notas": a.notas, "panel": a.panel}.items() if v}
    if cambios:
        p.update(cambios); guardar_json(PERFIL, p); print("✅ Perfil guardado.")
    if not p:
        print("Sin perfil. Ejemplo:\n  python3 ghl.py perfil --nombre \"Ana\" --agencia \"Mi Agencia\" --pais CL "
              "--tono \"cercano, tuteo\" --notas \"reportes los lunes\""); return
    jprint(p)


# ───────────────────────────── otros módulos de marketing (lectura) ─────────────────────────────
def cmd_marketing(a):
    g = Ghl(cuenta_activa(a.cuenta)); L = g.loc
    if a.que == "blogs":
        r = g.ok("GET", "/blogs/site/all", params={"locationId": L, "skip": 0, "limit": 50})
        for b in r.get("data") or []:
            print(f"· {b.get('name')}  id={b.get('_id') or b.get('id')}")
        if a.blog:
            r = g.ok("GET", "/blogs/posts/all", params={"locationId": L, "blogId": a.blog, "limit": 20, "offset": 0})
            for p in r.get("blogs") or r.get("data") or []:
                print(f"   - {p.get('status','')} {str(p.get('publishedAt') or p.get('updatedAt'))[:10]} {p.get('title')}")
        return
    if a.que == "correos":
        r = g.ok("GET", "/emails/schedule", params={"locationId": L, "limit": 50})
        print("Campañas de correo:")
        for x in r.get("schedules") or []:
            print(f"· {x.get('status') or '':<10} {x.get('name')}  id={x.get('id')}")
        r = g.ok("GET", "/emails/builder", params={"locationId": L, "limit": 50})
        print("Plantillas:")
        for x in r.get("builders") or []:
            print(f"· {x.get('name')}  ({x.get('templateSource')}, {str(x.get('lastUpdated'))[:10]})")
        return
    if a.que == "enlaces":
        r = g.ok("GET", "/links/", params={"locationId": L})
        for x in r.get("links") or []:
            print(f"· {x.get('name')} → {x.get('redirectTo')}  {x.get('fieldKey','')}")
        if not r.get("links"): print("(sin enlaces rastreables)")
        return
    if a.que == "marca":
        jprint(g.ok("GET", f"/brand-boards/{L}"), 6000); return
    if a.que == "medios":
        r = g.ok("GET", "/medias/files", params={"altId": L, "altType": "location", "type": "file", "limit": a.limite,
                                                  "sortBy": "createdAt", "sortOrder": "desc"})
        for f in r.get("files") or []:
            print(f"· {str(f.get('createdAt'))[:10]} {f.get('contentType') or '':<12} {float(f.get('size') or 0)/1e6:6.1f} MB  {f.get('name')}  id={f.get('_id')}  {f.get('url','')}")
        return


def cmd_api(a):
    """Llamada libre a cualquier endpoint (ver docs/MAPA-API.md). GET libre; lo demás exige --si."""
    g = Ghl(cuenta_activa(a.cuenta))
    path = a.ruta.replace("{locationId}", g.loc)
    body = json.loads(a.body) if a.body else None
    if a.metodo.upper() != "GET" and not a.si:
        print(f"⛔ {a.metodo.upper()} {path} cambia datos. Si es correcto, repite con --si."); return
    s, r = g.call(a.metodo.upper(), path, body=body, params=dict(x.split("=", 1) for x in a.param or []),
                  version=a.version)
    print("HTTP", s)
    jprint(r, None if a.json_completo else 12000)
    if a.metodo.upper() != "GET":
        bitacora("api", cuenta=g.c["alias"], metodo=a.metodo.upper(), ruta=path, http=s)


# ───────────────────────────── ACTUALIZAR ─────────────────────────────
REPO = "ervin-mo/ghl-marketing-agentico"
URL_VERSION = os.environ.get("GHL_VERSION_URL") or f"https://raw.githubusercontent.com/{REPO}/main/version.json"
REVISION = os.path.join(DIR, "actualizacion.json")
NO_TOCAR = ("informes/", "exportes/", ".git/", ".ghl-datos/")


def _vt(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3]) or (0,)


def ultima_version(timeout=8):
    """{'version','zip','sha256','notas'} publicada, o lanza Alto si no se pudo leer."""
    req = urllib.request.Request(URL_VERSION, headers={"User-Agent": f"ghl-marketing-agentico/{VERSION}",
                                                       "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode())
    except Exception as e:
        raise Alto(f"No pude revisar si hay versión nueva ({type(e).__name__}).\n   → " + SIN_RED)
    if not d.get("version") or not d.get("zip"):
        raise Alto("El aviso de versión publicado está incompleto.")
    return d


def revisar_version(forzar=False, horas=24):
    """La versión publicada si es más nueva que la instalada; None si estás al día. Usa caché de 24 h."""
    cache = {}
    if os.path.exists(REVISION):
        try:
            with open(REVISION, encoding="utf-8") as h:
                cache = json.load(h)
        except ValueError:
            cache = {}
    ahora = dt.datetime.now(dt.timezone.utc)
    try:
        fresca = ahora - dt.datetime.fromisoformat(cache.get("revisado", "")) < dt.timedelta(hours=horas)
    except ValueError:
        fresca = False
    if forzar or not fresca or not cache.get("ultima"):
        cache = {"revisado": ahora.isoformat(timespec="seconds"), "ultima": ultima_version()}
        try:
            guardar_json(REVISION, cache)
        except OSError:
            pass
    u = cache["ultima"]
    return u if _vt(u["version"]) > _vt(VERSION) else None


def aviso_version():
    """Una línea al final de cualquier comando si hay versión nueva. Nunca frena ni falla."""
    if os.environ.get("GHL_SIN_AVISO"):
        return
    try:
        u = revisar_version()
        if u:
            print(f"\nℹ️  Hay una versión nueva ({u['version']}; tienes {VERSION}). Actualiza con: python3 ghl.py actualizar",
                  file=sys.stderr)
    except Exception:
        pass


def cmd_actualizar(a):
    u = revisar_version(forzar=True)
    if a.json:
        jprint({"instalada": VERSION, "publicada": (u or {}).get("version", VERSION), "hay_nueva": bool(u),
                "notas": (u or {}).get("notas")}); return
    if not u:
        print(f"✅ Ya tienes la última versión ({VERSION})."); return
    print(f"Hay una versión nueva: {u['version']} (tienes {VERSION}).")
    if u.get("notas"):
        print("\nNovedades:\n" + u["notas"].strip() + "\n")
    if a.revisar:
        print("Para instalarla: python3 ghl.py actualizar"); return
    if os.path.isdir(os.path.join(AQUI, ".git")):
        print("Esta carpeta es una copia de git: actualizo con git pull…")
        r = subprocess.run(["git", "-C", AQUI, "pull", "--ff-only"], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        if r.returncode:
            die("git pull no pudo (¿cambios tuyos sin guardar en la carpeta?). Resuélvelo o descarga el zip de nuevo.")
        print(f"✅ Actualizado a {u['version']}."); return
    import tempfile, zipfile
    tmp = tempfile.mkdtemp(prefix="ghlmk-act-")
    zpath = os.path.join(tmp, "nuevo.zip")
    print("Descargando…")
    try:
        req = urllib.request.Request(u["zip"], headers={"User-Agent": f"ghl-marketing-agentico/{VERSION}"})
        with urllib.request.urlopen(req, timeout=120) as r, open(zpath, "wb") as h:
            shutil.copyfileobj(r, h)
    except Exception as e:
        die(f"No pude descargar la versión nueva ({type(e).__name__}). Intenta más tarde.")
    with open(zpath, "rb") as h:
        sha = hashlib.sha256(h.read()).hexdigest()
    if u.get("sha256") and sha != u["sha256"]:
        die("El archivo descargado no coincide con el publicado (sha256 distinto). No instalé nada; intenta más tarde.")
    with zipfile.ZipFile(zpath) as z:
        nombres = [n for n in z.namelist() if not n.endswith("/")]
        raiz = os.path.commonprefix([n.split("/")[0] + "/" for n in nombres]) if nombres else ""
        archivos = []
        for n in nombres:
            rel = n[len(raiz):] if raiz and n.startswith(raiz) else n
            if not rel or rel.startswith(("/", "\\")) or ".." in rel.replace("\\", "/").split("/") or ":" in rel:
                die(f"El paquete trae una ruta no válida ({n}). No instalé nada.")
            if rel.startswith(NO_TOCAR):
                continue
            archivos.append((n, rel))
        if not any(rel == "ghl.py" for _, rel in archivos):
            die("El paquete no trae ghl.py. No instalé nada.")
        respaldo = os.path.join(DIR, "respaldos", VERSION)
        os.makedirs(respaldo, exist_ok=True)
        for n, rel in archivos:
            destino = os.path.join(AQUI, *rel.split("/"))
            if os.path.isfile(destino):
                os.makedirs(os.path.dirname(os.path.join(respaldo, rel)), exist_ok=True)
                shutil.copy2(destino, os.path.join(respaldo, rel))
        for n, rel in sorted(archivos, key=lambda x: x[1] == "ghl.py"):   # ghl.py al final
            destino = os.path.join(AQUI, *rel.split("/"))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with z.open(n) as src, open(destino + ".nuevo", "wb") as dst:
                shutil.copyfileobj(src, dst)
            os.replace(destino + ".nuevo", destino)
    shutil.rmtree(tmp, ignore_errors=True)
    bitacora("actualizado", de=VERSION, a=u["version"], archivos=len(archivos))
    print(f"✅ Actualizado a {u['version']} ({len(archivos)} archivos). Tus subcuentas, PIT, fichas, metas, informes y "
          f"exportes no se tocaron.\n   La versión anterior quedó respaldada en {respaldo}")


# ───────────────────────────── línea de comandos ─────────────────────────────
def main():
    ap = argparse.ArgumentParser(prog="ghl.py", description="Marketing de GoHighLevel por API (PIT de subcuenta).")
    ap.add_argument("--version", action="version", version=VERSION)
    sub = ap.add_subparsers(dest="cmd")

    def con_cuenta(p):
        p.add_argument("--cuenta", help="alias de la subcuenta (por defecto: la marcada con ★ en «cuentas»)")
        p.add_argument("--json", action="store_true", help="salida en JSON")
        p.add_argument("--json-completo", action="store_true", help="JSON sin recortar")
        return p

    p = sub.add_parser("conectar", help="cargar el PIT de una subcuenta")
    p.add_argument("--pit"); p.add_argument("--location"); p.add_argument("--nombre"); p.add_argument("--usuario")
    p.add_argument("--zona"); p.add_argument("--default", action="store_true")
    p.add_argument("--sin-llavero", action="store_true", help="guardar el PIT en archivo en vez del Llavero")
    p = sub.add_parser("cuentas", help="ver, elegir o quitar subcuentas conectadas")
    p.add_argument("--usar"); p.add_argument("--quitar")
    con_cuenta(sub.add_parser("diagnostico", help="qué permisos tiene el PIT y qué está conectado"))

    p = con_cuenta(sub.add_parser("redes", help="Social Planner: cuentas, posts, métricas, crear/programar"))
    p.add_argument("accion", choices=["cuentas", "posts", "post", "metricas", "top", "categorias", "tags", "subir",
                                      "crear", "editar", "borrar", "lote", "revisar"])
    p.add_argument("id", nargs="?", help="id del post (post, editar, borrar)")
    p.add_argument("--estado", default="recent", choices=["recent", "all", "scheduled", "draft", "failed", "in_review",
                                                          "published", "in_progress", "deleted"])
    p.add_argument("--limite", type=int, default=20); p.add_argument("--saltar", type=int, default=0)
    p.add_argument("--desde", help="AAAA-MM-DD"); p.add_argument("--hasta", help="AAAA-MM-DD")
    p.add_argument("--cuantos-leer", type=int, default=200, help="top: cuántos posts revisar")
    p.add_argument("--redes", help="fb,ig,tiktok,linkedin,threads,google,youtube,pinterest,x,bluesky")
    p.add_argument("--cuentas-ids", "--cuentas-id", dest="cuentas_ids", help="ids exactos de cuentas (redes cuentas)")
    p.add_argument("--formato", "--tipo", dest="formato", default=None, choices=["post", "reel", "story"],
                   help="crear: post (por defecto), reel o story · posts: filtrar por formato")
    p.add_argument("--texto"); p.add_argument("--texto-archivo")
    p.add_argument("--media", help="archivos locales o URLs separados por coma (orden = carrusel)")
    p.add_argument("--primer-comentario"); p.add_argument("--categoria"); p.add_argument("--etiquetas")
    p.add_argument("--cuando", help="programar: '2026-11-12 10:00' (hora de la subcuenta), 'mañana 9:00', '+30m'")
    p.add_argument("--si", action="store_true", help="confirmo programar/borrar")
    p.add_argument("--repetir", action="store_true"); p.add_argument("--vista-previa", action="store_true")
    p.add_argument("--forzar", action="store_true", help="programar aunque la revisión marque 🔴")
    p.add_argument("--sin-ligas", action="store_true", help="no comprobar que las ligas abran")
    p.add_argument("--programados", action="store_true", help="revisar: todo lo programado")
    p.add_argument("--dias", type=int, help="revisar --programados: cuántos días hacia adelante (14)")
    p.add_argument("archivos", nargs="*", help=argparse.SUPPRESS)

    p = con_cuenta(sub.add_parser("ads", help="Meta Ads por Ad Manager de GHL: reportes y campañas"))
    p.add_argument("accion", choices=["verificar", "cuentas", "reporte", "campanas", "buscar", "formularios", "audiencias",
                                      "pixeles", "crear", "publicar", "estado", "pausar", "reanudar", "borrar"])
    p.add_argument("id", nargs="?", help="id de campaña de GHL (publicar/estado/pausar/reanudar/borrar) o spec (crear)")
    p.add_argument("--nivel", default="cuenta", choices=["cuenta", "campana", "conjunto", "anuncio"])
    p.add_argument("--campana", help="id de campaña de Meta (reporte por conjunto/anuncio)")
    p.add_argument("--desde"); p.add_argument("--hasta"); p.add_argument("--dias", type=int)
    p.add_argument("--todas", action="store_true", help="incluir campañas sin gasto")
    p.add_argument("--tipo", default="interest", choices=["interest", "geolocation", "language"])
    p.add_argument("--texto"); p.add_argument("--pagina"); p.add_argument("--act")
    p.add_argument("--si", action="store_true"); p.add_argument("--pausar", action="store_true")

    p = con_cuenta(sub.add_parser("marketing", help="blogs, correos, enlaces, marca y medios (lectura)"))
    p.add_argument("que", choices=["blogs", "correos", "enlaces", "marca", "medios"])
    p.add_argument("--blog"); p.add_argument("--limite", type=int, default=20)

    p = con_cuenta(sub.add_parser("api", help="llamada libre a cualquier endpoint de GHL"))
    p.add_argument("metodo"); p.add_argument("ruta", help="p. ej. /social-media-posting/{locationId}/accounts")
    p.add_argument("--body"); p.add_argument("--param", action="append", help="clave=valor (repetible)")
    p.add_argument("--version", default=V_SOCIAL, help="header Version (2021-07-28; v3 para anuncios)")
    p.add_argument("--si", action="store_true")

    def con_rango(p):
        p.add_argument("--desde", help="AAAA-MM-DD"); p.add_argument("--hasta", help="AAAA-MM-DD")
        p.add_argument("--dias", type=int, help="últimos N días completos"); p.add_argument("--mes", help="AAAA-MM")
        return p

    p = con_rango(sub.add_parser("agencia", help="varios clientes: resumen, alertas, calendario"))
    p.add_argument("accion", choices=["resumen", "alertas", "calendario"])
    p.add_argument("--cuentas", help="solo estas subcuentas (alias separados por coma); por defecto todas")
    p.add_argument("--borradores", action="store_true", help="calendario: incluir borradores pendientes")
    p.add_argument("--sin-crm", action="store_true", help="no leer el CRM (más rápido)")
    p.add_argument("--json", action="store_true")

    con_rango(con_cuenta(sub.add_parser("analisis", help="qué contenido funciona: red, formato, día, hora, largo")))
    p = con_rango(con_cuenta(sub.add_parser("informe", help="informe del periodo para el cliente (Markdown)")))
    p.add_argument("--salida"); p.add_argument("--mostrar", action="store_true", help="imprimirlo además de guardarlo")
    p.add_argument("--sin-crm", action="store_true", help="sin la sección de anuncio a venta")
    p = con_rango(con_cuenta(sub.add_parser("exportar", help="CSV: posts, anuncios por día o por conjunto")))
    p.add_argument("que", choices=["posts", "ads-diario", "ads-campanas"]); p.add_argument("--salida")
    p = sub.add_parser("perfil", help="quién usa el repo: nombre, agencia, país, tono (lo lee el agente)")
    for k in ("nombre", "agencia", "pais", "tono", "notas"):
        p.add_argument("--" + k)
    p.add_argument("--panel", help="URL de tu panel de GHL si es marca blanca (para las ligas a los chats)")

    p = con_rango(con_cuenta(sub.add_parser("crm", help="CRM: embudo de anuncio a venta, chats sin respuesta, etapas")))
    p.add_argument("accion", choices=["embudo", "atencion", "etapas"])
    p.add_argument("--horas", type=float, help="atencion: cuántas horas sin respuesta cuentan como pendiente")
    p.add_argument("--muestra", type=int, default=30, help="atencion: chats para medir el tiempo de respuesta (0 = no medir)")
    p.add_argument("--todas", action="store_true", help="atencion: listar todas las pendientes")

    p = sub.add_parser("metas", help="metas por cliente: posts por semana, costo máximo, leads, ventas, horas de respuesta")
    p.add_argument("--cuenta")
    for k, (tp, d) in METAS.items():
        p.add_argument("--" + k.replace("_", "-"), dest=k, help=d)
    p.add_argument("--quitar", help="campos a borrar, separados por coma")

    p = sub.add_parser("ficha", help="ficha de marca del cliente (tono, prohibidas, hashtags) que usa el agente al escribir")
    p.add_argument("--cuenta"); p.add_argument("--crear", action="store_true"); p.add_argument("--rehacer", action="store_true")
    p.add_argument("--actualizar-estilo", action="store_true"); p.add_argument("--ruta", action="store_true")
    p.add_argument("--abrir", action="store_true")

    p = sub.add_parser("actualizar", help="instalar la última versión (tus datos no se tocan)")
    p.add_argument("--revisar", action="store_true", help="solo decir si hay versión nueva")
    p.add_argument("--json", action="store_true")
    sub.add_parser("ayuda", help="ejemplos")
    a = ap.parse_args()
    if a.cmd in (None, "ayuda"):
        print(__doc__); print(AYUDA); aviso_version(); return
    if a.cmd == "redes" and a.accion == "subir":
        a.archivos = ([a.id] if a.id else []) + a.archivos
    if a.cmd == "ads" and a.accion == "crear":
        a.spec = a.id
        if not a.spec: die("ads crear <spec.json>")
    if a.cmd == "ads" and a.accion == "buscar" and not a.texto:
        a.texto = a.id
    try:
        {"conectar": cmd_conectar, "cuentas": cmd_cuentas, "diagnostico": cmd_diagnostico, "redes": cmd_redes,
         "ads": cmd_ads, "marketing": cmd_marketing, "api": cmd_api, "agencia": cmd_agencia,
         "analisis": cmd_analisis, "informe": cmd_informe, "exportar": cmd_exportar, "perfil": cmd_perfil,
         "crm": cmd_crm, "metas": cmd_metas, "ficha": cmd_ficha, "actualizar": cmd_actualizar}[a.cmd](a)
        if a.cmd not in ("actualizar",) and not getattr(a, "json", False):
            aviso_version()
    except Alto as e:
        print(f"⛔ {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n(cancelado)", file=sys.stderr)
        sys.exit(130)


AYUDA = """
EJEMPLOS
  Conectar y revisar
    python3 ghl.py conectar                         # pega el PIT y el locationId
    python3 ghl.py cuentas                          # subcuentas conectadas (★ = por defecto)
    python3 ghl.py cuentas --usar tienda-sol     # cambiar la de por defecto
    python3 ghl.py diagnostico                      # qué permisos tiene el PIT

  Redes sociales (Social Planner)
    python3 ghl.py redes cuentas                    # redes conectadas y cuándo vencen
    python3 ghl.py redes posts --estado published --limite 10
    python3 ghl.py redes posts --estado failed      # los que fallaron y por qué
    python3 ghl.py redes metricas                   # últimos 7 días vs 7 anteriores
    python3 ghl.py redes top --desde 2026-10-01     # los posts con más interacción
    python3 ghl.py redes crear --redes fb,ig --texto "Hola" --media foto.jpg          # BORRADOR
    python3 ghl.py redes crear --redes fb,ig --texto-archivo copy.txt --media a.jpg,b.jpg \\
        --cuando "2026-11-12 10:00" --si           # PROGRAMADO (hora de la subcuenta)
    python3 ghl.py redes crear --redes ig --formato reel --media video.mp4 --texto "…" --vista-previa
    python3 ghl.py redes lote ejemplos/parrilla.json          # plan de una parrilla; con --si la crea
    python3 ghl.py redes borrar <id> --si

  Anuncios de Meta (por Ad Manager de GHL)
    python3 ghl.py ads verificar
    python3 ghl.py ads reporte --dias 7             # toda la cuenta
    python3 ghl.py ads reporte --nivel campana --desde 2026-11-01 --hasta 2026-11-09
    python3 ghl.py ads reporte --nivel conjunto --campana <idMeta> --dias 7
    python3 ghl.py ads buscar --tipo geolocation --texto "Santiago"
    python3 ghl.py ads crear ejemplos/campana-whatsapp.json --si   # borrador
    python3 ghl.py ads publicar <idGHL> --si        # ⚠️ empieza a gastar ya

  Varios clientes (agencia)
    python3 ghl.py agencia resumen --dias 7         # todos los clientes: redes + anuncios vs. periodo anterior
    python3 ghl.py agencia alertas                  # lo que necesita atención (redes vencidas, fallidos, parrilla vacía…)
    python3 ghl.py agencia calendario --dias 14 --borradores
    python3 ghl.py agencia resumen --cuentas tienda-sol,clinica-norte --mes 2026-10

  Análisis e informes (un cliente)
    python3 ghl.py analisis --dias 90               # qué red, formato, día y hora funcionan mejor
    python3 ghl.py informe --mes 2026-10            # informe Markdown para el cliente (carpeta informes/)
    python3 ghl.py exportar posts --dias 90         # CSV para Excel/Sheets (carpeta exportes/)
    python3 ghl.py exportar ads-diario --mes 2026-10
    python3 ghl.py exportar ads-campanas --dias 30

  CRM: de anuncio a venta y atención (solo lectura; nunca muestra nombres ni teléfonos)
    python3 ghl.py crm embudo --mes 2026-10         # leads → oportunidades → ventas, costo por lead y por venta
    python3 ghl.py crm atencion                     # chats que esperan respuesta (con liga) y tiempo de respuesta
    python3 ghl.py crm etapas                       # qué etapas del embudo cuentan como venta

  Metas y ficha de marca (por cliente, viven en tu computadora)
    python3 ghl.py metas --cuenta tienda-sol --posts-semana 4 --costo-max 2500 --responder-horas 2 --leads-mes 120
    python3 ghl.py metas                            # las metas de todos
    python3 ghl.py ficha --cuenta tienda-sol --crear   # ficha con tono, prohibidas y hashtags (prellenada)
    python3 ghl.py ficha --cuenta tienda-sol        # leerla

  Revisión antes de programar (también corre sola al crear o programar)
    python3 ghl.py redes revisar --redes fb,ig --texto-archivo copy.txt --media foto.jpg --cuando "2026-11-20 10:00"
    python3 ghl.py redes revisar --programados      # todo lo programado de los próximos 14 días

  Mantenerlo al día
    python3 ghl.py actualizar --revisar             # ¿hay versión nueva?
    python3 ghl.py actualizar                       # instalarla (tus subcuentas, PIT, fichas y metas no se tocan)

  Otros
    python3 ghl.py perfil --nombre "Ana" --agencia "Mi Agencia" --pais CL --tono "cercano, tuteo"
    python3 ghl.py marketing correos | blogs | enlaces | marca | medios
    python3 ghl.py api GET /social-media-posting/{locationId}/categories
"""

if __name__ == "__main__":
    main()

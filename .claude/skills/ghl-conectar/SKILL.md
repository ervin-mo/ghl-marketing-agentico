---
name: ghl-conectar
description: Conecta una subcuenta de GoHighLevel con su PIT (token de integración privada) y revisa qué puede hacer el agente en ella. Úsalo cuando digan "conecta la subcuenta de X", "tengo el PIT de X", "agrega un cliente", "qué permisos tiene el token", "por qué no me deja publicar / leer anuncios", "cambia a la cuenta de X", o al empezar a trabajar con una subcuenta que todavía no aparece en `python3 ghl.py cuentas`.
---

# Conectar una subcuenta de GHL

La herramienta es `ghl.py`, en la raíz de este repo. Córrela siempre desde ahí (`python3 ghl.py …`).

## Pasos

1. `python3 ghl.py cuentas` — si la subcuenta ya está, no hay que conectar nada: `cuentas --usar <alias>`.
2. Si no está, la persona necesita su **PIT** y su **locationId**. Mándala a `docs/PIT.md` (cómo crearlo y qué
   scopes marcar). **Nunca le pidas que pegue el PIT en el chat.** Dile que corra ella misma:
   ```bash
   python3 ghl.py conectar
   ```
   Son 3 preguntas: el PIT (no se ve al pegarlo), el locationId **o la URL completa de la subcuenta** (la herramienta
   saca el id sola) y quién es de los usuarios. Al terminar corre el diagnóstico sola.
   Si ya lo pegó en el chat y quiere que lo cargues tú, usa la variable de entorno (no queda en el historial de
   comandos): `GHL_PIT='pit-…' python3 ghl.py conectar --location '<URL o id>'` y no lo repitas nunca en tus respuestas.
   Recomiéndale después borrar ese mensaje del chat.
3. Explica el diagnóstico (o córrelo de nuevo: `python3 ghl.py diagnostico`) en lenguaje simple:
   - ✅ = ya se puede.
   - ❌ = falta un scope → Settings → Private Integrations → el token → Edit → marcarlo → Update (el token no cambia).
   - 🟡 = el permiso está, pero falta conectar algo en GHL (Facebook en Ad Manager, cuenta de reportes).
4. Si va a haber anuncios: `python3 ghl.py ads verificar` (ver `docs/PIT.md` §5).

## Reglas

- El PIT es una contraseña: no se imprime, no se escribe en notas ni en el repo. `conectar` lo guarda en el
  **Llavero del sistema** (Mac: Acceso a Llaveros; Linux: `secret-tool`). Si no hay Llavero (Windows), va a
  `~/.config/ghl-marketing/cuentas.json` con permisos solo para el usuario. `cuentas` muestra 🔐 o 📄.
- Quitar un cliente: `python3 ghl.py cuentas --quitar <alias>` (borra también su PIT del Llavero).
- Una vez por persona: `python3 ghl.py perfil --nombre … --agencia … --pais CL --tono "…"` (lo usa el agente).
- Un PIT de **agencia** no sirve: tiene que ser de la subcuenta.
- Para usar otra subcuenta en un solo comando: `--cuenta <alias>`. Antes de cualquier cambio, confirma en qué
  subcuenta estás (el plan que imprime cada comando dice el nombre).
- En una máquina sin archivo de cuentas (servidor, CI) funcionan las variables `GHL_PIT`, `GHL_LOCATION_ID`,
  `GHL_USER_ID` y `GHL_ZONA`.


## Si no tienes internet o no puedes guardar (Codex y otros agentes con sandbox)

Probado con Codex en Windows y en Mac (10-nov-2026). Síntomas: `getaddrinfo failed`, `Sin internet en este entorno`,
`sin conexión`, `HTTP 0` o `No tengo permiso para guardar en…`, aunque la computadora sí tenga internet.

1. **No es la herramienta ni el internet de la persona**: es tu sandbox, que bloquea la red o la escritura fuera de
   esta carpeta.
2. **Vuelve a correr el MISMO comando pidiendo permisos elevados** (fuera del sandbox), con la justificación
   «ghl.py necesita internet para hablar con la API de GoHighLevel».
3. Dile a la persona, en palabras simples: «Te va a aparecer una solicitud de aprobación: dale **Aprobar**. Si te
   ofrece no volver a preguntar para comandos que empiecen con `python ghl.py`, elige esa opción».
4. **No** le pidas que edite archivos de configuración ni que cambie el agente a «acceso completo».
5. En Windows el comando es `python`, no `python3`.

La carpeta ya trae `.codex/config.toml`, que abre la red para este proyecto si la persona confió en la carpeta. Si no
se puede escribir en `~/.config/ghl-marketing`, los datos se guardan solos en `.ghl-datos/` dentro de la carpeta.
Detalle en `AGENTS.md`, sección «Si eres Codex».

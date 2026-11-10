---
name: ghl-marketing-panel
description: Consulta el resto del panel de marketing de una subcuenta de GoHighLevel - blogs y sus artículos, campañas y plantillas de correo, enlaces rastreables, Brand Board (colores, logos, fuentes) y la biblioteca de imágenes y videos - y llama a cualquier endpoint de la API de GHL que no tenga comando propio, con el mapa completo de qué existe. Úsalo cuando digan "qué blogs tiene X", "qué correos se mandaron", "qué plantillas hay", "los colores de la marca", "qué imágenes hay en Medios", "¿se puede hacer X por API?", "llama a este endpoint".
---

# Panel de marketing y API libre

Herramienta: `python3 ghl.py` (raíz del repo).

| Qué | Comando |
|---|---|
| Blogs y artículos | `marketing blogs` · `marketing blogs --blog <id>` |
| Campañas y plantillas de correo | `marketing correos` |
| Enlaces rastreables | `marketing enlaces` |
| Brand Board | `marketing marca` |
| Biblioteca de medios | `marketing medios --limite 30` |

## ¿Se puede hacer X por API?

Lee `docs/MAPA-API.md`: cada fila dice la llamada, si hay comando y si se probó (✅) o solo está en la doc (🟡).
Si no hay comando:

```bash
python3 ghl.py api GET  "/social-media-posting/{locationId}/tags"
python3 ghl.py api GET  "/blogs/posts/all" --param locationId=<loc> --param blogId=<id> --param limit=10 --param offset=0
python3 ghl.py api POST "/blogs/posts" --body '{…}' --si          # cambia datos: exige --si y OK de la persona
python3 ghl.py api GET  "/ad-publishing/google/integration" --param locationId=<loc> --version v3
```

- `{locationId}` en la ruta se rellena solo con la subcuenta activa.
- Header `Version`: `2021-07-28` por defecto; **`v3` para todo `/ad-publishing`**.
- Una llamada 🟡 que funcione por primera vez: anótala en `docs/MAPA-API.md` (pasa a ✅) para el siguiente.
- Cualquier llamada que no sea GET cambia algo real: enséñale a la persona qué vas a mandar y espera su OK.

## Lo que la API no hace

Conectar redes o Facebook (OAuth), crear el PIT, responder comentarios de redes. Eso es en la pantalla de GHL.


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

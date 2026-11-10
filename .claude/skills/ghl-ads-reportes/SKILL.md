---
name: ghl-ads-reportes
description: Lee los resultados de Meta Ads (Facebook e Instagram) de una subcuenta de GoHighLevel por su Ad Manager, sin Pipeboard - gasto, impresiones, alcance, clics, CTR, CPM, frecuencia, conversaciones de WhatsApp, leads y costo por resultado, por cuenta, campaña, conjunto o anuncio y en cualquier rango de fechas. Las cifras cuadran con Meta. Úsalo cuando digan "cómo van los anuncios de X", "cuánto gastamos esta semana", "costo por conversación", "qué conjunto rinde más", "reporte de campañas", "qué campañas están activas", "compara la semana".
---

# Reportes de Meta Ads por GHL

Herramienta: `python3 ghl.py` (raíz del repo). Solo lectura: no pide permiso.

**Antes, una vez por subcuenta:** `python3 ghl.py ads verificar`. Si «Lectura de reportes» sale ❌, falta elegir la
cuenta en Settings → Integrations → Facebook → Manage → Settings → Ad Account (lo hace la persona en GHL;
`docs/PIT.md` §5).

| Pregunta | Comando |
|---|---|
| ¿Cómo va toda la cuenta? | `ads reporte --dias 7` · `ads reporte --desde 2026-11-01 --hasta 2026-11-09` |
| ¿Qué campaña gasta más? | `ads reporte --nivel campana --dias 30` |
| ¿Qué conjunto/anuncio rinde? | `ads reporte --nivel conjunto --campana <idMeta> --dias 7` · `--nivel anuncio` |
| ¿Qué está activo o pausado? | `ads campanas` |
| ¿Qué cuenta publicitaria usa? | `ads cuentas` (★) |
| Datos crudos | `--json` |

`--dias N` = los últimos N días **completos** (hasta ayer). El día de hoy todavía no está cerrado.

## Cómo armar el reporte

1. `ads reporte --dias 7` y `--desde/--hasta` de la semana anterior → comparar gasto, conversaciones y costo por conversación.
2. `ads reporte --nivel campana` → qué campañas gastaron.
3. Para cada campaña con gasto: `--nivel conjunto` y `--nivel anuncio` → el mejor y el peor por costo por resultado.
4. Recomendación corta: qué pausar, qué escalar, qué creativo cansado (frecuencia > 3 con CTR bajando).

## Cómo leer las cifras

- **El resultado correcto depende del objetivo:** WhatsApp/Messenger → conversaciones iniciadas; formulario →
  leads; tráfico → clics al enlace. Nunca uses el total de «results» de GHL: suma todas las acciones.
- `--nivel campana` no trae alcance ni conversaciones (limitación de GHL): para eso, `--nivel conjunto`.
- Ceros con todo en ✅ en `verificar` = no hubo entrega en ese rango, o la cuenta elegida no es la de la campaña.
  Compruébalo con `ads campanas` antes de afirmarlo.
- La moneda es la de la cuenta publicitaria (sale en `ads verificar`).


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

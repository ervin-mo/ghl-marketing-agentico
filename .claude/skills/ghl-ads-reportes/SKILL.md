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

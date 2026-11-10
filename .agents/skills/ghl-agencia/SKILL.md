---
name: ghl-agencia
description: Revisa TODOS los clientes (subcuentas de GoHighLevel conectadas) a la vez - tablero con redes y anuncios de cada uno contra el periodo anterior, alertas de lo que necesita atención (redes desconectadas o por vencer, posts fallidos, parrilla vacía, costo por resultado que se disparó, anuncios que dejaron de gastar, creativos cansados) y el calendario de lo programado con los días sin publicación. Úsalo cuando digan "cómo van mis clientes", "qué tengo que revisar hoy", "algún cliente con problemas", "resumen de la semana de todos", "qué hay programado esta semana", "quién no tiene contenido programado", "compara a los clientes", o para la rutina del lunes.
---

# Agencia: todos los clientes a la vez

Herramienta: `python3 ghl.py` (raíz del repo). Todo es **solo lectura**. Sin `--cuentas` recorre todas las subcuentas
conectadas; con `--cuentas a,b` solo esas. Rango: `--dias N` (últimos N días completos), `--mes AAAA-MM` o
`--desde/--hasta`. Por defecto, 7 días.

| Pregunta | Comando |
|---|---|
| ¿Cómo van todos? | `agencia resumen --dias 7` |
| ¿Qué necesita atención? | `agencia alertas` |
| ¿Qué sale esta semana y qué días quedan vacíos? | `agencia calendario --dias 14 [--borradores]` |
| Comparar el mes | `agencia resumen --mes 2026-10` |
| Datos para tabla o gráfico | agrega `--json` |

## Rutina del lunes (lo que más sirve)

1. `agencia alertas` → primero los 🔴: una red desconectada hace fallar todo lo programado; una parrilla vacía es
   un cliente que no publica esta semana.
2. `agencia resumen --dias 7` → quién subió y quién bajó. Ordena tu respuesta por urgencia, no por cliente.
3. `agencia calendario --dias 7 --borradores` → huecos de la semana y borradores esperando aprobación.
4. Entrega: una lista corta por cliente con **lo que hay que hacer** (reconectar X, programar N posts, revisar la
   campaña Y), no la salida completa.

## Cómo leer las alertas

| Alerta | Qué hacer |
|---|---|
| 🔴 Red desconectada / 🟡 por vencer | Reconectar en GHL → Marketing → Social Planner → Settings (requiere iniciar sesión en la red: un agente no puede) |
| 🔴 Posts fallidos | `redes posts --estado failed --cuenta X` → el motivo por red (skill `ghl-redes-publicar`) |
| 🔴 Nada programado / 🟡 parrilla delgada | Proponer parrilla y dejarla en borradores para aprobar |
| 🟡 Costo por resultado subió > 30 % | `ads reporte --nivel conjunto --campana … --cuenta X` → qué público o anuncio se encareció |
| 🟡 Anuncios dejaron de gastar | `ads campanas --cuenta X`: pausada, rechazada o sin saldo (el saldo se ve en Meta) |
| 🟡 Frecuencia > 3 / CTR cayó | Creativo cansado: sugerir creativo nuevo |

## CRM y metas en el tablero

- `agencia resumen` agrega, por cliente:
  - la línea **CRM**: leads, cuántos de anuncios, costo por lead, ventas y su valor, costo por venta y chats sin
    respuesta;
  - la línea **Metas**: ✓ o ✗ contra cada meta.

  Tarda unos segundos más por cliente. `--sin-crm` lo quita.
- `agencia alertas` además avisa de:
  - chats que esperan respuesta;
  - publicaciones programadas con problemas (las mismas reglas de la revisión, sin comprobar ligas);
  - meta de publicaciones o de costo no cumplida;
  - presupuesto del mes adelantado o atrasado;
  - leads o ventas del mes por debajo de la meta;
  - inversión sin leads marcados como de anuncios.
- Las metas se definen con la skill `ghl-cliente-ficha`; el embudo, con `ghl-crm-embudo`.

| Alerta nueva | Qué hacer |
|---|---|
| 🔴/🟡 Chats esperan respuesta | `crm atencion --cuenta X` → ligas a cada chat. Es lo más urgente: es gente que ya escribió |
| 🔴 Programadas con problemas | `redes revisar --programados --cuenta X` → corregir con `redes editar` |
| 🟡 Presupuesto adelantado/atrasado | Revisar presupuestos diarios de las campañas (`ads campanas`) |
| 🟡 Inversión sin leads de anuncios | Preguntar con qué etiqueta marca el CRM a esos leads → `metas --etiquetas-anuncio` |

## Cuidado

- El resumen compara contra el periodo **inmediatamente anterior de igual largo**.
- «Interacción» = likes + 2×comentarios + 3×compartidos de los posts del periodo; GHL no entrega alcance por post.
- Un cliente con ⚠️ (error) no se analizó: dilo, no lo des por «sin novedades».

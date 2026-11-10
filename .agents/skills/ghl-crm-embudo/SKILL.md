---
name: ghl-crm-embudo
description: Mide lo que pasa DESPUÉS del anuncio en el CRM de una subcuenta de GoHighLevel - leads nuevos por origen (anuncios, redes, otro), oportunidades por etapa, ventas y su valor, costo por lead y por venta, retorno de la inversión; y la ATENCIÓN - chats que esperan respuesta (con liga directa al chat) y tiempo de respuesta. Solo lectura y sin mostrar nombres ni teléfonos. Úsalo cuando digan "cuántos leads llegaron", "cuántas ventas dejó la campaña", "cuánto me cuesta cada venta", "vale la pena lo que invertimos", "de los que escribieron cuántos compraron", "hay mensajes sin contestar", "quién está esperando respuesta", "qué tan rápido contestamos", "en qué etapa están los leads".
---

# CRM: de anuncio a venta, y atención

Herramienta: `python3 ghl.py` (raíz del repo). **Todo es solo lectura.** La herramienta nunca imprime nombres,
teléfonos ni el texto de los mensajes: solo cuenta, y para los chats pendientes da la liga al chat en GHL.
Necesita 4 permisos en el PIT (`contacts.readonly`, `opportunities.readonly`, `conversations.readonly`,
`conversations/message.readonly`); `diagnostico` dice si están.

| Pregunta | Comando |
|---|---|
| ¿Cuántos leads, de dónde, cuántas ventas y cuánto costó cada una? | `crm embudo --cuenta X --mes 2026-10` (o `--dias 30`) |
| ¿Quién espera respuesta? ¿Qué tan rápido contestamos? | `crm atencion --cuenta X` |
| ¿Qué etapa cuenta como venta? | `crm etapas --cuenta X` |
| Todos los clientes | `agencia resumen` (línea «CRM») y `agencia alertas` |

## `crm embudo`: cómo cuenta

- **Leads nuevos** = contactos creados en el rango. Se comparan con el periodo anterior de igual largo.
- **Origen «anuncios»**: el contacto trae una etiqueta de anuncio (`ad`, `ads`, `anuncio`, `pauta`, `paid`, `leadgen`…
  p. ej. `fb-ad-lead-whatsapp`) **o** su atribución trae un id de anuncio, `fbclid`/`gclid` o `utm_medium` pagado.
  «Redes» = vino de Facebook/Instagram/TikTok sin señal de anuncio. Si el cliente marca sus leads con otra etiqueta:
  `metas --cuenta X --etiquetas-anuncio "meta-lead,campaña-nov"`.
- **Ventas** = oportunidades marcadas como ganadas **o** que llegaron en el rango a una etapa de venta. Por defecto
  cuentan las etapas con «ganado», «cliente», «vendido», «cerrado», «pagado»; si un embudo no tiene ninguna, las
  que tienen ✅ o 🏆. Se cambia con `metas --etapas-venta "Cita agendada,Cliente"`. **Antes de dar cifras de ventas
  de un cliente nuevo, corre `crm etapas` y confirma con la persona qué es «venta» para ese negocio.**
- **Costo por lead / por venta** = inversión en anuncios del rango ÷ leads o ventas **que vinieron de anuncios**.
- **Retorno** = valor de las ventas de anuncios ÷ inversión. Usa el «valor» de la oportunidad en GHL: si el equipo no
  lo llena, el retorno sale bajo o vacío. Dilo.
- «Dónde están hoy» = las oportunidades creadas en el rango, por etapa actual.

## `crm atencion`: cómo cuenta

- Pendiente = el último mensaje lo mandó el cliente y lleva más de N horas sin respuesta (N = `metas
  --responder-horas`, por defecto 2; o `--horas 4`). Revisa los últimos 7 días (`--dias`).
- No cuenta los que terminan en «gracias», «ok», 👍 y parecidos (lo dice aparte).
- **Tiempo de respuesta**: mide en una muestra de 30 chats (`--muestra N`, 0 = no medir) el tiempo entre que escribe
  el cliente y la siguiente respuesta. **Incluye respuestas automáticas (bots y flujos)**: si el cliente tiene bot,
  sale casi en 0 y eso no dice cuánto tarda una persona.
- Las ligas abren el chat en GHL. Si la agencia usa marca blanca: `perfil --panel https://app.miagencia.com`.

## Cómo entregarlo

- Lead → venta como embudo corto: «420 leads (300 de anuncios) → 60 oportunidades → 12 ventas ($1.800.000). Cada venta de
  anuncios costó $45.000; por cada $1 invertido volvieron $3,20». (Cifras de ejemplo.)
- Si hay inversión y **0 leads de anuncios**, no concluyas que los anuncios no traen nada: falta la etiqueta.
  Pregunta cómo marca el CRM a esos leads y configúrala.
- Chats pendientes: cuántos, el más viejo y las ligas. Es lo primero que hay que atender: es gente que ya escribió.

## Nunca

- Copiar nombres, teléfonos o mensajes de los contactos a un informe, un chat o un archivo.
- Presentar el costo por venta sin decir qué se contó como venta.


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

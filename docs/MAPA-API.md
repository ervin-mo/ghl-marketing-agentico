# Mapa de la API de marketing de GHL

Qué se puede hacer con un PIT de subcuenta, qué cubre `ghl.py` y qué se probó en vivo.
Base `https://services.leadconnectorhq.com`, header `Authorization: Bearer <PIT>` y `Version`
(`2021-07-28` para todo salvo anuncios, que usa `v3`). Fuente: OpenAPI oficial
(`github.com/GoHighLevel/highlevel-api-docs/apps/*.json`) y pruebas del 5 y 10-nov-2026.

**Leyenda:** ✅ probado en vivo · 🟡 en la doc oficial, sin probar · ⛔ no existe por API

Lo que `ghl.py` no trae como comando se puede llamar igual con
`python3 ghl.py api <MÉTODO> <ruta> [--body '{…}'] [--param k=v] [--version v3] [--si]`
(`{locationId}` en la ruta se rellena solo; todo lo que no sea GET exige `--si`).

## 1. Redes sociales — Social Planner (`/social-media-posting`)

| Qué | Llamada | `ghl.py` | Estado |
|---|---|---|---|
| Redes conectadas, vencimiento, ids | `GET /{loc}/accounts` | `redes cuentas` | ✅ |
| Listar posts por estado y fechas | `POST /{loc}/posts/list` (`type`: recent, all, scheduled, draft, failed, in_review, published, in_progress, deleted; `limit`/`skip` **como texto**) | `redes posts` | ✅ |
| Ver un post (estado, error por red, liga) | `GET /{loc}/posts/{id}` | `redes post <id>` | ✅ |
| Crear borrador | `POST /{loc}/posts` con `status: draft` | `redes crear …` | ✅ |
| Programar | `POST /{loc}/posts` con `status: scheduled` + `scheduleDate` | `redes crear … --cuando … --si` | ✅ (en producción desde abr-2026) |
| Editar | `PUT /{loc}/posts/{id}` | `redes editar <id> …` | ✅ |
| Borrar | `DELETE /{loc}/posts/{id}` | `redes borrar <id> --si` | ✅ |
| Borrar varios | `POST /{loc}/posts/bulk-delete` | `api` | 🟡 |
| Métricas (7 días vs 7 anteriores: impresiones, alcance, likes, comentarios, compartidos, seguidores, edad y género) | `POST /statistics?locationId=` con `profileIds` | `redes metricas` | ✅ |
| Interacción por post (likes, comentarios, compartidos) | viene en `posts/list` → `insights` | `redes top` | ✅ |
| Categorías y etiquetas | `GET /{loc}/categories` · `GET /{loc}/tags` · `POST /{loc}/tags/details` | `redes categorias` / `tags` | ✅ |
| Carga masiva por CSV | `POST /{loc}/csv` · `GET/PATCH/DELETE /{loc}/csv/{id}` | `redes lote` (JSON, post por post) | 🟡 CSV · ✅ lote |
| Conectar redes (OAuth de FB, IG, LinkedIn, TikTok, X, Google) | `GET /oauth/<red>/start` … | — | ⛔ para un agente: abre una ventana de login; se hace en la pantalla de GHL |
| Quitar una red conectada | `DELETE /{loc}/accounts/{id}` | `api` | 🟡 (no usar sin querer: desconecta la red) |

**Formatos que ya salieron en producción por API (cuentas de la agencia y de clientes, abr–nov 2026):** imagen, carrusel de IG,
reel de IG/FB, video de FB, historia de IG, solo texto en FB, primer comentario.
**Redes:** Facebook, Instagram, TikTok Business, LinkedIn (página), Threads, Google Business, YouTube.

**Trampas medidas:**

- La hora mínima es +2 min (la herramienta exige +5). «Programado» no es «publicado»: revisa `--estado failed` después.
- `userId` es obligatorio aunque el PIT autentique (`conectar` lo guarda).
- Solo texto: `media: []` explícito o da 422.
- Un post «padre» se parte en un post por red; al listar `published` aparecen los hijos.
- Borrar un post **publicado** solo lo quita de GHL, no de la red.
- **Threads** a veces no puede bajar el medio de `filesafe.space` («could not fetch the media»).
- **TikTok** no acepta carruseles de imágenes (solo video).
- **YouTube** solo video; con canal sin verificar rechaza la miniatura.
- **Historias de IG** fallan si el IG está conectado vía Facebook y no directo.
- Personalizar el texto por red = un post por red (no hay campos por red, salvo `tiktokPostDetails` y `gmbPostDetails`).
- Los agentes mandan `\n` literal: la herramienta lo convierte en salto de línea.

## 2. Imágenes y videos (`/medias`)

| Qué | Llamada | `ghl.py` | Estado |
|---|---|---|---|
| Subir (25 MB imagen, 500 MB video) | `POST /medias/upload-file` multipart (`file`, `name`, `hosted=false`) | `redes subir` (y solo dentro de `crear`) | ✅ |
| Listar | `GET /medias/files?altId&altType=location&type=file` | `marketing medios` | ✅ |
| Borrar | `DELETE /medias/{id}?altId&altType=location` | `api` (y `ads borrar` limpia los suyos) | ✅ |

## 3. Anuncios de Meta — Ad Manager (`/ad-publishing/facebook`, `Version: v3`)

**Requisito:** Facebook conectado en Marketing → Ad Manager y, para leer campañas hechas en Meta, la cuenta
elegida en Settings → Integrations → Facebook → Settings → Ad Account (ver `PIT.md` §5).

| Qué | Llamada | `ghl.py` | Estado |
|---|---|---|---|
| Estado de la conexión | `GET /integration` (⚠️ trae tokens de página: la herramienta los oculta) | `ads verificar` | ✅ |
| Cuentas publicitarias | `GET /ad-accounts` · `GET /ad-accounts/{act}` | `ads cuentas` | ✅ |
| Reporte de la cuenta (cifras = Meta) | `GET /reporting?type=INTEGRATION&fields=…&startDate&endDate` | `ads reporte` | ✅ cuadró peso por peso con Meta |
| Reporte por campaña / conjunto / anuncio | `GET /reporting/list?listType=campaigns\|adsets\|ads[&campaignId]` | `ads reporte --nivel …` | ✅ |
| Campañas que hay en Meta y su estado | `GET /entity?type=INTEGRATION&entityType=CAMPAIGN` | `ads campanas` | ✅ |
| Buscar intereses, ciudades, idiomas | `GET /targeting/search?type=interest\|geolocation\|language&query` | `ads buscar` | ✅ |
| Formularios de leads | `GET/POST /page/{pageId}/forms` | `ads formularios` | ✅ |
| Audiencias personalizadas, píxeles | `GET /custom-audience` · `GET /pixels` | `ads audiencias` / `pixeles` | ✅ lectura |
| Crear campaña, conjunto, anuncio (borrador) | `PUT /campaigns` · `PUT /adsets` · `PUT /ads` | `ads crear <spec> --si` | ✅ |
| Publicar en Meta | `POST /campaigns/{id}/publish` → `GET …/publishing-progress` | `ads publicar <id> --si` | ✅ |
| Pausar / reanudar / duplicar | `POST /campaigns\|adsets\|ads/{id}/pause\|resume\|duplicate` | `ads pausar/reanudar`, `api` | ✅ |
| Borrar | `DELETE /campaigns/{id}` con `{locationId}` **en el cuerpo** | `ads borrar <id> --si` | ✅ |
| Editar audiencias, miembros, píxeles | `PUT /custom-audience/…` · `PUT /pixels` | `api` | 🟡 |
| Google Ads y LinkedIn Ads | `/ad-publishing/google/*` · `/ad-publishing/linkedin/*` (reportes, campañas, palabras clave) | `api` | 🟡 (ninguna subcuenta probada los tiene conectados) |

**Trampas medidas:**

- 🚨 **GHL ignora la fecha de inicio**: publicar = empieza a gastar en ese momento.
- Solo se **editan** campañas que nacieron en GHL. Las de Meta Ads Manager se leen y se reportan, pero no se tocan.
- Los medios deben estar subidos a GHL (una URL externa falla al publicar); `ads crear` los sube solo.
- Textos como `[{"text": …}]` (la herramienta los envuelve); carrusel: `link` en cada tarjeta; video: `miniatura`.
- `totals.results` suma TODAS las acciones: no es «resultados». Usa conversaciones, clics o leads por separado.
- `listType=campaigns` no trae alcance ni conversaciones: para eso, `--nivel conjunto`.
- Audiencias muy chicas: Meta pide ampliar. Leads: la página debe aceptar las condiciones
  (`facebook.com/ads/leadgen/tos?page_id=…`) y el formulario necesita aviso de privacidad.
- 429 de Meta («too many calls»): esperar ~10 min.

## 4. Otros módulos de marketing

| Qué | Llamada | `ghl.py` | Estado |
|---|---|---|---|
| Blogs y sus artículos | `GET /blogs/site/all` · `GET /blogs/posts/all?blogId` | `marketing blogs [--blog id]` | ✅ lectura |
| Crear / editar artículo de blog | `POST /blogs/posts` · `PUT /blogs/posts/{id}` | `api` | 🟡 |
| Campañas y plantillas de correo | `GET /emails/schedule` · `GET /emails/builder` | `marketing correos` | ✅ lectura |
| Crear / editar plantilla de correo | `POST /emails/builder` · `POST /emails/builder/data` | `api` | 🟡 |
| Enlaces rastreables (trigger links) | `GET/POST /links/` · `PUT/DELETE /links/{id}` | `marketing enlaces` | ✅ lectura |
| Brand Board (colores, logos, fuentes) | `GET /brand-boards/{loc}` · `POST/PATCH` | `marketing marca` | ✅ lectura |
| Responder comentarios y DMs de redes | — | — | ⛔ no hay endpoint público de comentarios del Social Planner; los DMs van por Conversations |
| Reportes de Instagram/Facebook orgánico por post (alcance por post) | — | — | ⛔ solo likes/comentarios/compartidos por post y totales semanales |

## 5. Lo que NO hace la API (y hay que hacer en pantalla)

- Conectar o reconectar redes (OAuth): Marketing → Social Planner → Settings.
- Conectar Facebook para anuncios y elegir la cuenta de reportes.
- Crear o editar el PIT y sus scopes.
- Aprobar posts con el flujo de aprobación de GHL (sí se puede mandar `postApprovalDetails`, 🟡).

## 7. CRM: de anuncio a venta y atención (solo lectura)

Probado el 10-nov-2026 en dos subcuentas, contando sin imprimir datos de contactos.

| Qué | Llamada | `ghl.py` | Estado |
|---|---|---|---|
| Contactos creados en un rango | `POST /contacts/search` con `filters: [{field: dateAdded, operator: range, value: {gte, lte}}]`, `pageLimit` hasta 500, `page` | `crm embudo` | ✅ |
| Embudos y etapas | `GET /opportunities/pipelines?locationId=` | `crm etapas` | ✅ |
| Oportunidades | `GET /opportunities/search?location_id=&date=MM-DD-AAAA&endDate=…&limit=100`; paginar con `startAfter` + `startAfterId` de `meta` | `crm embudo` | ✅ |
| Conversaciones por último mensaje | `GET /conversations/search?locationId=&sort=desc&sortBy=last_message_date&limit=100`; paginar con `startAfterDate` | `crm atencion` | ✅ |
| Mensajes de un chat | `GET /conversations/{id}/messages?limit=100` → `messages.messages[]` | `crm atencion` (tiempo de respuesta) | ✅ |

**Trampas medidas:**
- **El origen casi nunca está en la atribución.** En una subcuenta con anuncios de WhatsApp, menos del 10 % de los
  contactos del mes traía `attributionSource.medium = facebook`, pero la mayoría tenía una etiqueta tipo
  `fb-ad-lead-whatsapp` puesta por su integración. Por eso el origen se lee de las etiquetas **y** de la atribución.
- **Casi nadie usa «ganado/perdido».** En las subcuentas probadas no había ninguna oportunidad `won`: la venta es una
  etapa (por ejemplo «✅ Cliente» o «Servicio realizado ✅»). Por eso la venta se detecta por etapa y se configura por cliente.
- La oportunidad trae `contact.tags` y `attributions[]`: se clasifica sin pedir el contacto.
- `lastStageChangeAt` dice cuándo entró a la etapa actual (sirve para «ventas en el periodo»).
- `conversations/search` trae `lastMessageDirection` (`inbound`/`outbound`), `lastMessageDate` en milisegundos,
  `unreadCount` y `isLastMessageInternalComment`. El filtro `lastMessageDirection=inbound&status=unread` también funciona.
- Con proveedores externos de WhatsApp (`TYPE_CUSTOM_SMS`), el bot y las personas salen igual (`source: api`): el
  tiempo de respuesta incluye respuestas automáticas.
- **Sin cabecera `User-Agent`, Cloudflare de GHL responde 403 «Error 1010»** al `urllib` de Python. `ghl.py` ya la manda.
- Los mensajes tipo `TYPE_ACTIVITY_*` (citas, cambios de etapa) no son respuestas: se ignoran.

## 8. Funciones compuestas (varias llamadas por detrás)

| `ghl.py` | Qué combina | Estado |
|---|---|---|
| `agencia resumen` | por cada subcuenta: `posts/list` (publicados del periodo y del anterior, fallidos, programados 14 días) + `accounts` (vencimientos) + `reporting` (periodo y anterior) | ✅ |
| `agencia alertas` | lo mismo + reglas: red vencida o que vence en < 7 días, fallidos, nada programado o ≤ 1 día con publicación en 7, costo por resultado ±30 %, anuncios sin gasto, frecuencia > 3, CTR −30 % | ✅ |
| `agencia calendario` | `posts/list` programados (y borradores) por día en la zona de cada subcuenta | ✅ |
| `analisis` | hasta 1.500 posts publicados con su `insights`, agrupados por red, formato, día, franja, largo y pregunta | ✅ |
| `informe` | lo de `agencia resumen` + `statistics` + `reporting/list` de campañas y conjuntos → Markdown | ✅ |
| `exportar ads-diario` | una llamada a `reporting` por día (GHL no acepta `groupBy=date`) | ✅ |
| `crm embudo` | `contacts/search` (periodo y anterior) + `pipelines` + `opportunities/search` de 12 meses + `reporting` → leads por origen, ventas, costo por lead y por venta, retorno | ✅ |
| `crm atencion` | `conversations/search` de 7 días + `messages` de una muestra → chats pendientes y tiempo de respuesta | ✅ |
| `redes revisar` | `accounts` (vencimientos) + `posts/list` (repetidos) + la ficha del cliente + comprobación de ligas y medidas de archivos | ✅ |

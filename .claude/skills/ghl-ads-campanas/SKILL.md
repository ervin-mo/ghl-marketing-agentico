---
name: ghl-ads-campanas
description: Crea, publica, pausa, reanuda y borra campañas de Meta Ads (Facebook e Instagram) por el Ad Manager de una subcuenta de GoHighLevel, sin Pipeboard - objetivo WhatsApp, Messenger, tráfico o formulario de leads; imagen, video o carrusel; audiencia por país, ciudad con radio, edad, intereses e idioma; presupuesto por conjunto o por campaña. Se arma en borrador, se revisa y se publica con OK. Úsalo cuando digan "lánzale una campaña a X", "monta la campaña de WhatsApp", "sube estos creativos a Meta", "pausa la campaña", "duplica el anuncio", "busca el id de Santiago para la audiencia".
---

# Campañas de Meta por GHL

Herramienta: `python3 ghl.py` (raíz del repo). **Nunca se gasta un peso sin OK de la persona para esa campaña.**

## Orden

1. **¿La subcuenta está lista?** `ads verificar` → todo ✅. Para leads, además, «Condiciones de leads» ✅ y un
   formulario (`ads formularios`).
2. **Armar el spec** copiando `ejemplos/campana-whatsapp.json` o `ejemplos/campana-trafico-carrusel.json`:

   | Quiere | `objective` | En el conjunto | En el anuncio |
   |---|---|---|---|
   | Mensajes a WhatsApp | `OUTCOME_ENGAGEMENT` | `"messagingPlatforms": ["WHATSAPP"]` | `"cta": "MESSAGE_PAGE"` |
   | Messenger | `OUTCOME_ENGAGEMENT` | `["MESSENGER"]` | `"MESSAGE_PAGE"` |
   | Leads con formulario | `OUTCOME_LEADS` | `"conversionLocation": "on_ad"` | `"destinationFormId"`, `"cta": "SIGN_UP"` |
   | Visitas a la web | `OUTCOME_TRAFFIC` | — | `"destinationLink"`, `"cta": "LEARN_MORE"`/`"SHOP_NOW"` |

   - `pageId`: sale en `ads verificar`.
   - Audiencia: `ads buscar --tipo geolocation --texto "Santiago"` · `--tipo interest --texto "moda"` ·
     `--tipo language --texto Spanish` → copiar `key`/`id`, `name`, `type`. Ciudad con `"radius": 15, "radiusUnit": "km"`.
     Intereses muy chicos hacen que Meta rechace: mejor amplio o sin intereses.
   - Presupuesto en la **moneda de la cuenta** (CLP en Chile: `5000` = $5.000 diarios).
     Por campaña: `"isCampaignBudget": true, "bidStrategy": "LOWEST_COST_WITHOUT_CAP", "budget": {…}` en `campana` y
     sin `budget` en el conjunto.
   - Creativos: `{"archivo": "ruta.jpg"}`; video `{"archivo": "x.mp4", "miniatura": "portada.jpg"}`; carrusel
     `"mediaType": "CAROUSEL"` y cada tarjeta con `link` (+ `headline`, `description`). Imagen ≤ 25 MB, video ≤ 500 MB.
   - Varias variantes en `primaryTexts` y `headlines` (Meta las rota).
   - Nombres: `Cliente · Objetivo · Oferta · dd-mmm-aaaa`.
3. **Crear en borrador:** `ads crear spec.json` (enseña el plan) → `ads crear spec.json --si`. No toca Meta ni gasta.
4. **Enseñarlo:** objetivo, presupuesto diario y total estimado, zona y público, cada anuncio con su texto, destino.
   Pregunta: «¿La lanzo?».
5. **Publicar, solo con su sí:** `ads publicar <idGHL> --si`. 🚨 **Empieza a gastar en ese momento** (GHL ignora la
   fecha de inicio). Si debe arrancar otro día, publica ese día.
6. **Confirmar:** `ads estado <idGHL>` → cada anuncio `IN_REVIEW`/`PUBLISHED` y `rechazo_meta` vacío. Si Meta rechazó
   algo, el motivo está ahí (carrusel sin `link`, audiencia chica, política…).
7. A las 24–48 h: `ads reporte --nivel anuncio --campana <idMeta>` (skill `ghl-ads-reportes`).

## Operar

```bash
python3 ghl.py ads pausar <idGHL>            # libre: deja de gastar
python3 ghl.py ads reanudar <idGHL> --si     # vuelve a gastar
python3 ghl.py ads borrar <idGHL> --si       # la quita de Meta y limpia sus medios
python3 ghl.py api POST "/ad-publishing/facebook/ads/<adId>/duplicate" --body '{"locationId":"…"}' --version v3 --si
```

## Lo que no se puede

- Editar campañas creadas en Meta Ads Manager (se leen y se reportan, pero no se tocan desde aquí).
- Programar la fecha de inicio, reglas automáticas, pruebas A/B.
- Pruebas: una campaña de prueba se crea en **borrador** y se borra; nunca se publica en la cuenta de un cliente.

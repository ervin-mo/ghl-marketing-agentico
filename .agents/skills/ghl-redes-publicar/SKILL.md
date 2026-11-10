---
name: ghl-redes-publicar
description: Crea, programa, edita y borra publicaciones en las redes de una subcuenta de GoHighLevel (Social Planner) - post con imagen, carrusel, reel, video, historia o solo texto, en Facebook, Instagram, TikTok, LinkedIn, Threads, Google Business y YouTube, con primer comentario y parrillas completas desde un archivo. Por defecto deja BORRADORES; programar exige confirmación. Úsalo cuando digan "programa este post", "sube el carrusel", "publica el reel el jueves a las 10", "déjalo en borrador", "carga la parrilla de la semana", "cambia el copy del post", "borra el post programado". Reemplaza a Upload Post para las subcuentas conectadas.
---

# Publicar y programar en redes (Social Planner)

Herramienta: `python3 ghl.py` (raíz del repo). La hora se escribe en la **zona de la subcuenta**
(la guardó `conectar`; sale en el plan).

## 🚦 La regla de oro

| Qué | ¿Necesita OK de la persona? |
|---|---|
| `redes crear` **sin** `--cuando` → **BORRADOR** (no sale a ninguna red) | No |
| `--vista-previa` (enseña el plan, no crea nada) | No |
| `--cuando … --si` → **PROGRAMADO** (va a salir solo a esa hora) | **Sí, para ESE post:** red, hora y texto |
| `redes borrar <id> --si` | **Sí** |
| `redes lote parrilla.json --si` | **Sí, para esa parrilla** (enséñale el plan primero) |

Sin `--si` la herramienta solo imprime el plan y se detiene. Si la persona ya dio el texto final, el archivo y
la hora y dijo «prográmalo», ese es el OK: no se lo vuelvas a pedir.

## Comandos

```bash
# Borrador (seguro): queda en GHL → Marketing → Social Planner para revisarlo
python3 ghl.py redes crear --redes fb,ig --texto-archivo copy.txt --media foto.jpg

# Programado
python3 ghl.py redes crear --redes fb,ig --texto-archivo copy.txt --media a.jpg,b.jpg,c.jpg \
    --primer-comentario "#hashtags" --cuando "2026-11-20 10:00" --si

# Reel / historia
python3 ghl.py redes crear --redes ig,fb --formato reel --media reel.mp4 --texto-archivo copy.txt --cuando "mañana 18:30" --si
python3 ghl.py redes crear --redes ig --formato story --media historia.jpg --cuando "+30m" --si

# Pasar un borrador a programado, o cambiarle algo
python3 ghl.py redes editar <id> --redes fb,ig --texto-archivo copy.txt --media foto.jpg --cuando "2026-11-20 10:00" --si

# Parrilla completa (formato en ejemplos/parrilla.json; rutas de media relativas al archivo)
python3 ghl.py redes lote parrilla.json          # plan
python3 ghl.py redes lote parrilla.json --si     # crea: con "cuando" = programado, sin "cuando" = borrador

python3 ghl.py redes borrar <id> --si
```

- **Texto:** para algo de más de una línea usa `--texto-archivo` (evita líos con comillas, acentos y emojis).
- **Media:** rutas locales (se suben solas a la biblioteca de GHL) o URLs, separadas por coma. El orden es el
  orden del carrusel.
- **Varias cuentas de la misma red:** `--cuentas-ids <id1,id2>` (ids en `redes cuentas`).
- **Texto distinto por red:** un comando por red.

## Formatos por red

| Red | Admite | Texto máx. | Primer comentario |
|---|---|---|---|
| Facebook | imagen, carrusel, video, reel, historia, solo texto | 62 000 | ✅ |
| Instagram | imagen, carrusel, reel (9:16, 3–90 s), historia | 2 200 | ✅ |
| TikTok | **solo video** (no carruseles) | 2 200 | ❌ |
| LinkedIn (página) | imagen, video, texto | 3 000 | ✅ |
| Threads | imagen, video, texto | 500 | ✅ |
| Google Business | imagen y texto | 1 500 | ❌ |
| YouTube | solo video | — | ❌ |

Historias: sin texto (la herramienta lo vacía); video de historia ≤ 60 s.

## Revisión antes de programar (corre sola)

Cada `redes crear`, `editar` y `lote` revisa el post antes de crear nada e imprime `REVISIÓN`.
**Si hay un 🔴 y el post va programado, no lo programa** (`--forzar` solo si la persona lo pide sabiendo el
problema). En borradores solo avisa.

| Revisa | Nivel |
|---|---|
| Red desconectada, o cuya conexión **vence antes de la hora** del post | 🔴 |
| Relleno sin completar: `[LINK]`, `{{nombre}}`, `TODO`, `XXX`, `lorem ipsum` | 🔴 |
| Texto más largo de lo que admite cada red · más de 30 hashtags en Instagram | 🔴 |
| Palabra prohibida de la ficha del cliente | 🔴 |
| Liga rota (404, 410, 5xx o el dominio no existe) | 🔴 |
| Red que necesita imagen o video y no lleva · reel sin video · más archivos de los que admite la red | 🔴 |
| Conexión que vence en menos de 7 días · faltan los hashtags fijos de la ficha · texto casi igual a otro post de los últimos 30 días | 🟡 |
| Liga en el texto de Instagram (no se puede tocar) · teléfono en Google Business · primer comentario en TikTok/Google | 🟡 |
| Imagen chica (menos de 600 px), que Instagram recorta, o que no es 9:16 en reel/historia · video de historia de más de 60 s o reel de más de 3 min · archivos pesados | 🟡 |
| Hora entre 23:00 y 7:00 | 🟡 |

```bash
python3 ghl.py redes revisar --redes fb,ig --texto-archivo copy.txt --media foto.jpg --cuando "2026-11-20 10:00"  # solo revisa
python3 ghl.py redes revisar --programados            # todo lo programado de los próximos 14 días (--dias N)
```

- Sin conexión a internet o en sitios que bloquean robots, una liga sale 🟡 «no pude comprobarla»: ábrela a mano.
- La duración de los videos se mide si está `ffprobe` (viene con ffmpeg); si no, ese punto se salta.
- `--sin-ligas` se salta la comprobación de ligas (más rápido).

## Después de programar

1. Reporta: «Programado. Post `<id>`. Sale `<fecha y hora>` en `<redes>`. **Programado no es publicado.**»
2. Pasada la hora: `redes posts --estado failed`. Errores típicos: red vencida (reconectar en GHL), Threads que no
   baja el medio, TikTok con imágenes, YouTube sin verificar, historia de IG conectada vía Facebook.
3. Borrar un post **ya publicado** solo lo quita de GHL; en la red hay que borrarlo a mano.

## Nunca

- Programar o borrar sin OK, ni con el texto que tú inventaste sin que la persona lo haya visto.
- Repetir el mismo post en 30 min (la herramienta lo frena; `--repetir` solo si de verdad va dos veces).
- Publicar pruebas en las redes de un cliente: las pruebas son **borradores** que se borran enseguida.

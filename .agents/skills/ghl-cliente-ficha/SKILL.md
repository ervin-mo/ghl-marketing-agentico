---
name: ghl-cliente-ficha
description: Prepara a un cliente (subcuenta de GoHighLevel) para trabajarlo bien - su FICHA DE MARCA (qué vende, tono, trato tú/usted, emojis, hashtags fijos, palabras prohibidas, temas que no se tocan, ejemplos) que se usa para escribir con su voz y que la revisión de publicaciones aplica sola; y sus METAS (publicaciones por semana, costo máximo por resultado, presupuesto del mes, leads y ventas por mes, horas para contestar) contra las que se miden el resumen, las alertas y el informe. Úsalo cuando digan "dale de alta al cliente", "arma la ficha de X", "cómo habla esta marca", "qué no puede decir", "la meta es N posts por semana", "no debe pasar de $X por conversación", "el presupuesto del mes es…", "escríbeme la parrilla de X con su tono".
---

# Ficha de marca y metas de un cliente

Las dos viven en tu computadora (`~/.config/ghl-marketing/clientes/<alias>/`, o en `.ghl-datos/clientes/<alias>/` si usas Codex): actualizar el repo no
las borra.

## Ficha de marca

```bash
python3 ghl.py ficha --cuenta X --crear            # la arma prellenada
python3 ghl.py ficha --cuenta X                    # leerla
python3 ghl.py ficha --cuenta X --ruta             # dónde está (para editarla)
python3 ghl.py ficha --cuenta X --abrir            # abrirla en el editor
python3 ghl.py ficha --cuenta X --actualizar-estilo   # rehace solo «Cómo escribe hoy»
```

`--crear` toma de GHL la ciudad, la web y las redes, y **calcula de sus publicaciones** cómo escribe hoy:

- largo típico;
- trato (tú o usted);
- emojis;
- hashtags más usados;
- si pregunta o pone ligas.

Lo demás se llena con la persona. Hazle estas preguntas, una tanda corta:

1. ¿Qué vende y a quién? ¿Qué lo hace distinto?
2. ¿Tú o usted? ¿3 palabras para su estilo?
3. ¿Qué hashtags van siempre?
4. ¿Qué **no** se puede decir? (precios que no existen, «gratis», promesas, la competencia)
5. ¿Qué temas no se tocan?
6. ¿Algún post que le haya gustado mucho?

Escribe las respuestas en el archivo (`--ruta`) con tu herramienta de edición. **Respeta los títulos «## Palabras
prohibidas» y «## Hashtags fijos»** y deja cada elemento en una línea con guion: la revisión los lee de ahí y frena
cualquier post con una palabra prohibida.

### Escribir con la ficha

Antes de redactar posts o una parrilla para un cliente, **lee su ficha** y sigue su trato, largo, emojis y CTA.
Después:

1. Deja todo en **borrador**: `redes crear` sin `--cuando`, o `redes lote` con `--si` y sin `cuando` (skill
   `ghl-redes-publicar`).
2. La revisión corre sola en cada post. Corrige lo 🔴 antes de enseñárselo a la persona.

## Metas

```bash
python3 ghl.py metas --cuenta X --posts-semana 4 --costo-max 2500 --gasto-mes 300000 \
    --leads-mes 120 --ventas-mes 15 --responder-horas 2
python3 ghl.py metas --cuenta X --etiquetas-anuncio "fb-ad-lead,ig-ad-lead" --etapas-venta "Cliente" --pipeline "Ventas"
python3 ghl.py metas --cuenta X --quitar gasto_mes
python3 ghl.py metas                               # las de todos los clientes
```

| Meta | Qué se compara | Dónde aparece |
|---|---|---|
| `posts-semana` | Publicaciones por semana (un post en FB e IG cuenta como una) y lo programado para los próximos 7 días | resumen, alertas, informe |
| `costo-max` | Costo por resultado de anuncios (conversación, lead o clic) | 🔴 en alertas si se pasa |
| `gasto-mes` | Ritmo del gasto del mes: avisa si va adelantado (más de 115 %) o atrasado (menos de 70 %), con la proyección al cierre | alertas |
| `leads-mes` · `ventas-mes` | Ritmo del mes contra la meta | resumen, alertas, informe |
| `responder-horas` | Desde cuándo un chat sin contestar cuenta como pendiente | alertas, `crm atencion` |
| `etiquetas-anuncio` · `etapas-venta` · `pipeline` | Cómo se mide el embudo (skill `ghl-crm-embudo`) | embudo e informe |

- Montos sin símbolo. Para Chile, `2500` o `2.500` dan lo mismo.
- Sin metas, todo funciona igual, pero solo compara contra el periodo anterior.
- Al dar de alta un cliente, propón metas razonables partiendo de lo que ya hace:
  - `analisis`: cuánto publica;
  - `ads reporte --dias 30`: cuánto gasta y cuánto le cuesta cada resultado.

  La persona las confirma.


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

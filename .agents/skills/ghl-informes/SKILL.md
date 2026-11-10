---
name: ghl-informes
description: Analiza qué contenido funciona en una subcuenta de GoHighLevel (por red, formato, día, franja horaria, largo del texto, con o sin pregunta; mejores y peores posts), arma el informe del periodo para el cliente (redes + anuncios contra el periodo anterior, mejores publicaciones, campañas, alertas y próximos pasos) en Markdown, y exporta a CSV los posts, los anuncios por día o por conjunto para Excel o Google Sheets. Úsalo cuando digan "informe de octubre de X", "reporte mensual para el cliente", "qué tipo de post le funciona", "a qué hora conviene publicar", "pásame los datos a Excel", "gráfico del gasto por día".
---

# Análisis, informes y exportación (un cliente)

Herramienta: `python3 ghl.py` (raíz del repo). Solo lectura. `--cuenta <alias>` elige el cliente.
Rango: `--mes AAAA-MM`, `--dias N` o `--desde/--hasta`.

## Qué contenido funciona

```bash
python3 ghl.py analisis --cuenta X --dias 90
```

Interacción promedio por red, formato, día de la semana, franja horaria, largo del texto y con/sin pregunta, más los
5 mejores y 5 más flojos. **Al contarlo:** grupos con 1–2 posts no son concluyentes (dilo); recomienda solo lo que
tenga varios posts detrás; compara formatos dentro de la misma red cuando puedas.

## Informe para el cliente

```bash
python3 ghl.py informe --cuenta X --mes 2026-10            # guarda informes/X_2026-10-01_2026-10-31.md
python3 ghl.py informe --cuenta X --dias 30 --mostrar      # además lo imprime
```

Trae: resumen contra el periodo anterior (publicaciones, interacción, inversión, resultados y costo por resultado,
alcance de anuncios), redes por red, métricas de los últimos 7 días, mejores publicaciones con liga, tabla de
campañas, el público que mejor rindió, alertas y próximos pasos.

**Antes de entregarlo:**
1. Léelo entero y **reescribe «Próximos pasos»** con criterio (los automáticos son básicos), en el tono del perfil.
2. Revisa que los nombres de campaña sean presentables para el cliente (son los de Meta).
3. Si piden PDF, Word o Google Docs, conviértelo desde el Markdown con la herramienta que tengas.
4. **No lo mandes tú al cliente**: entrégalo a la persona para que lo revise.

## Exportar a CSV (Excel / Google Sheets)

```bash
python3 ghl.py exportar posts --cuenta X --dias 90          # un post por fila con likes, comentarios, compartidos y liga
python3 ghl.py exportar ads-diario --cuenta X --mes 2026-10 # un día por fila: gasto, impresiones, alcance, clics, CTR, CPM, conversaciones, leads
python3 ghl.py exportar ads-campanas --cuenta X --dias 30   # un conjunto por fila de las 6 campañas con más gasto
```

Se guardan en `exportes/` (UTF-8 con BOM: Excel respeta los acentos). Para un gráfico, el diario es el bueno.

## Límites de los datos (dilos si importan)

- GHL no da **alcance por publicación**: solo likes, comentarios y compartidos. Las historias no los tienen.
- Las métricas de cuenta de redes (impresiones, alcance, seguidores) solo existen para **los últimos 7 días**.
- Los anuncios sí van en cualquier rango y cuadran con Meta.

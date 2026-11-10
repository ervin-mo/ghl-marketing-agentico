---
name: ghl-redes-consultar
description: Consulta las redes sociales de una subcuenta de GoHighLevel (Social Planner) - qué redes están conectadas y cuándo vencen, qué se publicó, qué está programado o en borrador, qué falló y por qué, métricas de los últimos 7 días (impresiones, alcance, likes, comentarios, seguidores, edad y género) y los posts con más interacción. Úsalo cuando digan "cómo van las redes de X", "qué se publicó esta semana", "qué hay programado", "qué falló", "métricas de Instagram/Facebook", "cuál fue el mejor post", "arma un reporte de redes", "se venció alguna red".
---

# Consultar redes sociales (Social Planner)

Herramienta: `python3 ghl.py` (raíz del repo). Todo esto es **solo lectura**: córrelo sin pedir permiso.

| Pregunta | Comando |
|---|---|
| ¿Qué redes hay y si alguna se venció? | `redes cuentas` |
| ¿Qué se publicó? | `redes posts --estado published --limite 20 [--desde AAAA-MM-DD --hasta AAAA-MM-DD]` |
| ¿Qué está programado / en borrador? | `redes posts --estado scheduled` · `--estado draft` |
| ¿Qué falló y por qué? | `redes posts --estado failed` → `redes post <id>` (el error por red) |
| ¿Cómo vamos? (7 días vs 7 anteriores) | `redes metricas [--redes ig,fb]` |
| ¿Cuál pegó más? | `redes top --desde AAAA-MM-DD [--limite 10]` |
| Datos crudos para analizar | agrega `--json` (o `--json-completo`) |

Agrega `--cuenta <alias>` para otra subcuenta.

## Cómo armar un reporte de redes

1. `redes cuentas` → avisa primero si hay una red **vencida** o que vence en menos de 7 días: los posts a esa red
   van a fallar. Se reconecta en GHL → Marketing → Social Planner → Settings (un agente no puede hacerlo).
2. `redes metricas` → totales y cambio contra la semana anterior, por red.
3. `redes top --desde <hace 30 días>` → los 3–5 mejores con su liga, y qué tienen en común (formato, tema, hora).
4. `redes posts --estado failed` → lo que no salió.
5. `redes posts --estado scheduled` → lo que viene.
6. Cierra con 2–3 recomendaciones concretas (qué repetir, qué dejar, qué hueco de días hay en la parrilla).

## Cómo leer las cifras

- `metricas` siempre son **los últimos 7 días** contra los 7 anteriores (GHL no deja elegir el rango ahí).
  Para otro rango, usa `redes top`/`redes posts` con `--desde/--hasta` (interacción por post).
- La interacción por post trae likes, comentarios y compartidos; **no** trae alcance por post.
- Un 0 en una red que sí publica puede ser falta de permisos de estadísticas en esa conexión
  (`hasStatisticsPermissions` en `redes cuentas --json`), no un 0 real. Dilo así.
- «Programado» no es «publicado»: confírmalo con `--estado published`/`failed` después de la hora.

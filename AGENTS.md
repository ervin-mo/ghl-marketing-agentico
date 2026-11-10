# Instrucciones para el agente (Claude Code, Codex, OpenCode, DeepSeek Harness o cualquier otro)

Este repo te deja manejar **el marketing de una subcuenta de GoHighLevel (GHL) por API**: redes sociales
(Social Planner), anuncios de Meta (Ad Manager), métricas y el resto del panel de marketing. Así la persona te pide
las cosas en lenguaje normal y no tiene que entrar a la pantalla de GHL.

## La herramienta

`python3 ghl.py` en la raíz del repo. Python 3.9+ sin instalar nada. `python3 ghl.py ayuda` muestra todo.
Las credenciales (el PIT de cada subcuenta) viven en `~/.config/ghl-marketing/`, fuera del repo.

## Antes de usar cualquier skill: ¿hay versión nueva?

Una vez por sesión, antes del primer comando:

```bash
python3 ghl.py actualizar --revisar
```

- Si dice **«Ya tienes la última versión»**, sigue.
- Si dice **«Hay una versión nueva»**:
  1. Corre `python3 ghl.py actualizar`. Solo reemplaza los archivos del repo; las subcuentas, los PIT, las fichas, las
     metas, los informes y los exportes no se tocan.
  2. Cuéntale a la persona en una o dos líneas qué cambió (viene en «Novedades»).
  3. **Vuelve a leer este archivo y la skill que ibas a usar**: pudieron cambiar.
- Si no hay internet o falla la revisión, sigue con la versión instalada y dilo en una línea. No es motivo para parar.

## Las skills: abre la que toque ANTES de actuar

| Encargo | Skill |
|---|---|
| Conectar una subcuenta, revisar permisos del token, cambiar de cliente | `.claude/skills/ghl-conectar/SKILL.md` |
| Cómo van las redes, qué se publicó, qué falló, métricas, mejores posts | `.claude/skills/ghl-redes-consultar/SKILL.md` |
| Crear, programar, editar o borrar posts; parrillas completas | `.claude/skills/ghl-redes-publicar/SKILL.md` |
| Resultados de anuncios de Meta (gasto, conversaciones, costo por resultado) | `.claude/skills/ghl-ads-reportes/SKILL.md` |
| Crear, publicar, pausar o borrar campañas de Meta | `.claude/skills/ghl-ads-campanas/SKILL.md` |
| **Varios clientes a la vez**: cómo van todos, qué necesita atención, calendario | `.claude/skills/ghl-agencia/SKILL.md` |
| Qué contenido funciona, informe del mes para el cliente, exportar a Excel | `.claude/skills/ghl-informes/SKILL.md` |
| **De anuncio a venta**: leads, oportunidades, ventas, costo por venta; **chats sin respuesta** y tiempo de respuesta | `.claude/skills/ghl-crm-embudo/SKILL.md` |
| **Ficha de marca** del cliente (tono, prohibidas, hashtags) y sus **metas**; escribir con la voz del cliente | `.claude/skills/ghl-cliente-ficha/SKILL.md` |
| Blogs, correos, enlaces, Brand Board, medios; cualquier endpoint sin comando | `.claude/skills/ghl-marketing-panel/SKILL.md` |

Mapa completo de la API (qué existe, qué se probó, trampas): `docs/MAPA-API.md`.
Cómo crear el PIT y qué permisos marcar: `docs/PIT.md`.
Agente completo (tono, rutina, reglas): `.claude/agents/agente-marketing.md`. Antes de empezar, corre
`python3 ghl.py perfil` (quién te habla: país, moneda, tono) y `python3 ghl.py cuentas` (qué clientes puedes tocar).

## Reglas que no se rompen

1. **Leer es libre; cambiar pide permiso.** Consultar redes, métricas, reportes o el panel: sin preguntar.
   Programar, publicar, gastar en anuncios, reanudar o borrar: solo con un «sí» de la persona para ESE cambio,
   después de que vea el plan que imprime la herramienta. La herramienta lo obliga: sin `--si` no cambia nada.
2. **Un borrador no publica.** `redes crear` sin `--cuando` y `ads crear` dejan todo en borrador. Es la forma segura
   de preparar trabajo para que la persona lo revise.
3. **El PIT es una contraseña.** Nunca lo imprimas, nunca lo escribas en archivos del repo, notas o mensajes. Lo
   guarda `conectar` en el Llavero del sistema. Si la persona lo pega en el chat, cárgalo con
   `python3 ghl.py conectar --pit … --location …` y no lo repitas.
4. **Programado no es publicado.** Pasada la hora, confirma con `redes posts --estado failed`.
5. **Anuncios: publicar = gastar ya.** GHL ignora la fecha de inicio.
6. **Nada de pruebas en redes o anuncios de clientes.** Si hay que probar algo, que sea un borrador que se borra.
7. **Comprueba antes de afirmar.** Si un comando devuelve ceros o vacío, sospecha primero del filtro, la fecha o la
   subcuenta (`--cuenta`) antes de decir «no hay nada».
8. **Responde con conclusiones.** Cifras clave, qué cambió, qué recomiendas. No pegues JSON crudo a la persona.
9. **Los contactos del CRM no salen.** Nombres, teléfonos y mensajes de los clientes de la subcuenta no se copian a
   informes, chats ni archivos. La herramienta solo da cifras y ligas a los chats.
10. **Antes de escribir para un cliente, lee su ficha** (`python3 ghl.py ficha --cuenta X`). Si la revisión marca 🔴,
    se corrige; `--forzar` solo con el «sí» de la persona sabiendo el problema.

## Si eres Codex, OpenCode u otro agente sin «skills» nativas

Las skills son archivos Markdown normales: cuando el encargo calce con una fila de la tabla, ábrela con tu
herramienta de lectura y sigue sus pasos. (OpenCode y Codex también encuentran las skills en `.claude/skills/` y
`.agents/skills/`.)

# Cambios

## 1.3.1 — 10-nov-2026
- **Funciona en Codex, también en Windows.** El sandbox normal de Codex bloquea internet y no deja escribir fuera de la
  carpeta del proyecto; por eso `ghl.py` fallaba con `getaddrinfo failed`.
  - La carpeta trae `.codex/config.toml`, que abre la red solo para este proyecto. Codex lo lee si confías en la carpeta.
  - Si el agente aun así no tiene red, la herramienta se lo dice con un mensaje claro: que vuelva a correr el comando
    pidiendo aprobación. La persona solo da **Aprobar**.
  - Si no se puede escribir en `~/.config/ghl-marketing`, los datos van a `.ghl-datos/` dentro de la carpeta (fuera
    de git; las actualizaciones no la tocan).
  - `AGENTS.md` trae la sección «Si eres Codex» y avisa que en Windows el comando es `python`.
- `.agents/skills` ahora es una copia real (antes era un enlace simbólico, que en Windows no funciona con git).
- La bitácora y la caché de versión ya no tumban un comando si no se pueden escribir.

## 1.3.0 — 10-nov-2026
- **Se actualiza solo.** `python3 ghl.py actualizar` instala la última versión publicada en GitHub; `--revisar` solo
  avisa. Antes de instalar comprueba la huella (sha256) del archivo, respalda la versión anterior en
  `~/.config/ghl-marketing/respaldos/` y no toca subcuentas, PIT, fichas, metas, informes ni exportes. En una copia
  de git hace `git pull`.
- Al final de cualquier comando aparece un aviso si hay versión nueva (se revisa una vez al día; sin internet no
  estorba). `GHL_SIN_AVISO=1` lo apaga.
- Regla para el agente: antes de usar las skills revisa la versión y, si hay una nueva, la instala y cuenta qué cambió.
- Licencia aclarada: código visible, no de código abierto; uso solo con autorización de Escala+.

## 1.2.0 — 10-nov-2026
- **De anuncio a venta** (`crm embudo`): leads nuevos por origen (anuncios, redes, otro), oportunidades por etapa,
  ventas y su valor, costo por lead, costo por venta y retorno. El origen se detecta por etiquetas del CRM y por la
  atribución de Meta; las ventas, por estado «ganado» o por etapa. Las dos cosas se ajustan por cliente.
  `crm etapas` muestra qué etapas cuentan como venta.
- **Chats sin respuesta** (`crm atencion`): conversaciones que esperan respuesta hace más de N horas, con la liga a
  cada chat, y el tiempo de respuesta medido en una muestra. No muestra nombres ni mensajes.
- **Metas por cliente** (`metas`):
  - publicaciones por semana;
  - costo máximo por resultado;
  - presupuesto del mes;
  - leads y ventas del mes;
  - horas para contestar.

  Las usan el resumen, las alertas y el informe.
- **Ficha de marca** (`ficha`): se arma sola con la web, las redes y cómo escribe hoy el cliente (largo, tú o usted,
  emojis, hashtags). Sus palabras prohibidas y hashtags fijos los aplica la revisión.
- **Revisión antes de programar** (corre sola en `redes crear/editar/lote`, y aparte con `redes revisar`). Frena lo
  grave:
  - red desconectada o que vence antes de la hora;
  - ligas rotas;
  - rellenos sin completar;
  - texto o hashtags de más;
  - palabras prohibidas;
  - redes sin el medio que exigen.

  Avisa de imágenes chicas o mal proporcionadas, videos largos, textos repetidos y horas de madrugada.
  `redes revisar --programados` revisa lo ya programado.
- `agencia resumen` suma la línea CRM y el cumplimiento de metas; `agencia alertas` suma chats pendientes,
  programados con problemas, metas y ritmo del presupuesto. `informe` suma «De anuncio a venta» y «Metas».
- `diagnostico` revisa los 4 permisos nuevos de CRM. Skills nuevas `ghl-crm-embudo` y `ghl-cliente-ficha`.

## 1.1.0 — 10-nov-2026
- **Varios clientes:** `agencia resumen` (tablero de todos contra el periodo anterior), `agencia alertas` (redes
  desconectadas o por vencer, fallidos, parrilla vacía, costo por resultado, anuncios sin gasto, frecuencia y CTR) y
  `agencia calendario` (lo programado, días vacíos y borradores).
- **Análisis de contenido:** `analisis` por red, formato, día, franja horaria, largo del texto y con/sin pregunta.
- **Informe del periodo** para el cliente en Markdown: `informe --mes AAAA-MM`.
- **Exportar a CSV:** `exportar posts | ads-diario | ads-campanas`.
- **PIT en el Llavero del sistema** (Mac y Linux); `conectar` acepta la URL completa de la subcuenta y corre el
  diagnóstico al terminar. `cuentas --quitar` borra también el PIT del Llavero.
- **Perfil** de quien usa el repo (`perfil`): país, moneda y tono para el agente.
- Agente genérico `agente-marketing` (Claude Code y OpenCode). Skills nuevas `ghl-agencia` y `ghl-informes`.
- Montos con el formato del país de la subcuenta (Chile: `$150.000`).

## 1.0.0 — 10-nov-2026
- Primera versión: `conectar`, `diagnostico`, Social Planner (consultar, métricas, top, borradores, programar,
  parrillas, editar, borrar), anuncios de Meta por Ad Manager (reportes, campañas en borrador, publicar, pausar,
  borrar), blogs, correos, enlaces, Brand Board, medios y llamada libre a la API. 6 skills y `AGENTS.md`.

# GHL Marketing Agéntico

**Tu agente de IA trabajando en GoHighLevel por ti.** Le dices *«¿cómo van mis clientes esta semana?»*,
*«prográmame la parrilla del lunes al viernes a las 10»* o *«arma el informe de octubre»*, y lo hace por la API
oficial de GHL, sin que entres a la pantalla.

Funciona con **Claude Code, Codex, OpenCode, DeepSeek Harness** o cualquier agente que lea archivos y corra comandos.
Una sola herramienta en Python, sin instalar nada más, y un **token de integración privada (PIT)** por subcuenta.

---

## Qué puedes pedirle

### 📊 Varios clientes a la vez
- *«¿Cómo van todos mis clientes esta semana?»* → tablero con redes y anuncios de cada uno contra la semana anterior.
- *«¿Qué tengo que revisar hoy?»* → alertas: redes desconectadas o por vencer, publicaciones fallidas, parrilla vacía,
  costo por resultado que se disparó, anuncios que dejaron de gastar, creativos cansados.
- *«¿Qué sale esta semana y qué días quedan vacíos?»* → calendario de todos, con borradores por aprobar.

### 📱 Redes sociales (Social Planner)
- *«¿Qué se publicó, qué está programado y qué falló?»* (con el motivo de cada falla).
- *«¿Cómo van las métricas?»* → impresiones, alcance, likes, comentarios, seguidores, edad y género de los últimos 7 días.
- *«¿Qué tipo de contenido le funciona a este cliente?»* → por red, formato, día, hora, largo del texto; mejores y peores.
- *«Deja en borrador este carrusel»* · *«programa este reel el jueves 18:30»* · *«carga la parrilla del mes»*.
- Facebook, Instagram, TikTok, LinkedIn, Threads, Google Business y YouTube: imagen, carrusel, reel, video, historia
  y solo texto, con primer comentario.

### 💰 Anuncios de Meta (por el Ad Manager de GHL)
- *«¿Cuánto gastamos este mes y cuánto costó cada conversación?»* → por cuenta, campaña, conjunto o anuncio, en
  cualquier rango. Las cifras cuadran con Meta.
- *«¿Qué público rinde mejor? ¿Qué pausarías?»*
- *«Arma una campaña de WhatsApp para Santiago, $5.000 diarios, con estos dos creativos»* → queda en borrador; se
  publica solo cuando dices que sí.

### 🎯 De anuncio a venta (CRM, solo lectura)
- *«¿Cuántos leads dejó la campaña y cuántos compraron?»* → leads por origen (anuncios, redes, otro), oportunidades
  por etapa, ventas y su valor, **costo por lead, costo por venta y retorno** de lo invertido.
- *«¿Quién está esperando respuesta?»* → chats sin contestar hace más de 2 horas, con la liga a cada chat, y el
  tiempo de respuesta del equipo.
- Nunca muestra nombres, teléfonos ni mensajes de los contactos: solo cifras y ligas.

### 🧭 Cada cliente con su ficha y sus metas
- **Ficha de marca**: qué vende, tú o usted, emojis, hashtags fijos, palabras prohibidas, temas que no se tocan. Se
  arma sola con lo que ya publica y la completas con el cliente. El agente escribe con esa voz.
- **Metas**: publicaciones por semana, costo máximo por resultado, presupuesto del mes, leads y ventas del mes, horas
  para contestar. El resumen, las alertas y el informe dicen ✓ o ✗ contra cada una.

### ✅ Revisión antes de programar
Cada publicación se revisa antes de programarse:
- red desconectada o que vence antes de la hora;
- ligas rotas;
- `[LINK]` u otros rellenos sin completar;
- texto demasiado largo o con demasiados hashtags;
- palabras prohibidas del cliente;
- imágenes chicas o mal proporcionadas;
- reels sin video;
- textos repetidos;
- horas de madrugada.

Si hay algo grave, **no la programa**. También revisa todo lo que ya está programado.

### 📄 Informes y datos
- *«Informe de octubre para el cliente»* → documento listo para revisar: resumen contra el mes anterior, redes,
  mejores publicaciones, campañas, alertas y próximos pasos.
- *«Pásame los datos a Excel»* → CSV de publicaciones, anuncios por día o por conjunto.

### 🧩 El resto del panel
Blogs, campañas y plantillas de correo, enlaces rastreables, Brand Board, biblioteca de medios, y cualquier otro
endpoint de la API de GHL.

**Lo que publica, gasta, edita o borra siempre se detiene y te muestra el plan hasta que digas que sí.** Lo que el
agente prepara por su cuenta queda en **borrador**, que no sale a ninguna red.

---

## Instalar (3 minutos)

1. **Descarga** [la última versión](https://github.com/ervin-mo/ghl-marketing-agentico/releases/latest/download/ghl-marketing-agentico.zip)
   y descomprímela donde quieras (por ejemplo, en Documentos). Si usas git: `git clone https://github.com/ervin-mo/ghl-marketing-agentico.git`.
2. Abre la **Terminal** en esa carpeta (Mac: clic derecho en la carpeta → *Nuevo terminal en la carpeta*).
3. Comprueba que tienes Python 3.9 o más nuevo (en Mac ya viene):
   ```bash
   python3 --version
   python3 ghl.py ayuda
   ```
   *Windows: instala Python desde python.org (marca «Add to PATH») y usa `python` en lugar de `python3`.*

## Conectar tu subcuenta de GHL

1. **Crea el PIT** en la subcuenta: *Settings → Private Integrations → Create new*, marcando los permisos de la tabla de
   [`docs/PIT.md`](docs/PIT.md). Copia el token (empieza con `pit-`).
2. **Conéctala:**
   ```bash
   python3 ghl.py conectar
   ```
   Te hace 3 preguntas: pega el PIT (no se ve en pantalla), pega **la URL de la subcuenta** tal como está en tu
   navegador, y elige quién eres. Al terminar te muestra qué puede hacer el agente en esa subcuenta (✅ / ❌).
3. **¿Más clientes?** Repite `conectar` con el PIT de cada subcuenta. Las ves con `python3 ghl.py cuentas`.
4. **Una sola vez, tu perfil** (para que el agente use tu país, moneda y tono):
   ```bash
   python3 ghl.py perfil --nombre "Tu nombre" --agencia "Tu agencia" --pais CL --tono "cercano, tuteo"
   ```
5. **Por cada cliente, su ficha y sus metas** (o pídeselo al agente: *«dale de alta a este cliente»*):
   ```bash
   python3 ghl.py ficha --cuenta mi-cliente --crear
   python3 ghl.py metas --cuenta mi-cliente --posts-semana 4 --costo-max 2500 --responder-horas 2
   ```

### ¿Es seguro?

- El PIT se guarda en el **Llavero del sistema** (Mac y Linux), cifrado. En Windows queda en un archivo de tu carpeta
  personal que solo tu usuario puede leer. **Nunca dentro de esta carpeta**, así que puedes actualizarla o
  compartirla sin riesgo.
- La herramienta **nunca muestra el PIT** ni los tokens de Facebook que GHL incluye en algunas respuestas.
- Cada cambio queda anotado en `~/.config/ghl-marketing/bitacora.jsonl` (qué, cuándo, en qué subcuenta).
- Si un PIT se filtra: GHL → Settings → Private Integrations → bórralo y crea otro; luego `conectar` de nuevo.
- Cada PIT solo abre **su** subcuenta: el agente no puede tocar clientes que no conectaste.

---

## Usarlo con tu agente

Abre tu agente **dentro de la carpeta** y pídele las cosas normalmente.

| Agente | Cómo |
|---|---|
| **Claude Code** | `claude` en la carpeta → lee `CLAUDE.md` y las skills de `.claude/skills/` solo. Agente completo: *«usa el agente agente-marketing»* |
| **Codex** | `codex` en la carpeta → lee `AGENTS.md` y encuentra las skills en `.agents/skills/` |
| **OpenCode** | `opencode` en la carpeta → lee `AGENTS.md`; agente `agente-marketing` en `.opencode/agent/` |
| **DeepSeek Harness u otro** | Ábrelo en la carpeta y dile: *«lee AGENTS.md y sigue sus reglas»* |

### Una rutina que funciona

| Cuándo | Qué le pides |
|---|---|
| Lunes temprano | *«¿Qué tengo que revisar hoy en mis clientes?»* y *«¿qué días quedan vacíos esta semana?»* |
| Al armar contenido | *«Deja en borrador estos 5 posts para revisar»* → los apruebas en GHL o le dices *«prográmalos»* |
| Viernes | *«Resumen de la semana de todos»* |
| Fin de mes | *«Informe de este mes para cada cliente»* |
| Con anuncios | *«¿Qué conjunto rinde peor? ¿Qué harías?»* |

---

## Sin agente (comandos directos)

```bash
python3 ghl.py agencia resumen --dias 7          # todos los clientes
python3 ghl.py agencia alertas                   # lo que necesita atención
python3 ghl.py agencia calendario --dias 14 --borradores
python3 ghl.py redes metricas --cuenta mi-cliente
python3 ghl.py analisis --cuenta mi-cliente --dias 90
python3 ghl.py informe --cuenta mi-cliente --mes 2026-10
python3 ghl.py exportar ads-diario --cuenta mi-cliente --mes 2026-10
python3 ghl.py crm embudo --cuenta mi-cliente --mes 2026-10      # de anuncio a venta
python3 ghl.py crm atencion --cuenta mi-cliente                  # chats sin respuesta
python3 ghl.py redes revisar --programados --cuenta mi-cliente   # revisar lo programado
python3 ghl.py redes crear --redes fb,ig --texto-archivo copy.txt --media foto.jpg                         # borrador
python3 ghl.py redes crear --redes fb,ig --texto-archivo copy.txt --media foto.jpg --cuando "2026-11-20 10:00" --si
python3 ghl.py ads reporte --nivel campana --dias 30
```

`python3 ghl.py ayuda` muestra todos los comandos con ejemplos.

---

## Documentación

| Archivo | Para qué |
|---|---|
| [`docs/PIT.md`](docs/PIT.md) | Crear el token, qué permisos marcar, conectar varias subcuentas, requisitos de anuncios |
| [`docs/MAPA-API.md`](docs/MAPA-API.md) | Todo lo que permite la API de marketing de GHL, qué está probado y las trampas conocidas |
| [`AGENTS.md`](AGENTS.md) | Las reglas y el índice de skills que sigue el agente |
| `.claude/skills/*/SKILL.md` | Las 10 skills: conectar, consultar redes, publicar, reportes de anuncios, campañas, agencia, informes, CRM (anuncio a venta), ficha y metas, panel |
| [`CHANGELOG.md`](CHANGELOG.md) | Qué cambió en cada versión |

## Qué no hace (se hace en la pantalla de GHL)

Conectar o reconectar redes y Facebook (requieren iniciar sesión en cada red), crear el PIT, responder comentarios de
redes y editar campañas creadas directamente en Meta Ads Manager (esas sí se leen y se reportan). GHL tampoco entrega
alcance por publicación ni métricas de cuenta de redes fuera de los últimos 7 días.

## Actualizar

Se mantiene al día solo:

- **Con tu agente:** antes de trabajar revisa si hay versión nueva, la instala y te cuenta qué cambió.
- **Sin agente:** al final de cualquier comando aparece un aviso si hay versión nueva (se revisa una vez al día).
- **A mano:**

  ```bash
  python3 ghl.py actualizar --revisar    # ¿hay versión nueva?
  python3 ghl.py actualizar              # instalarla
  ```

**Qué no se toca al actualizar:** tus subcuentas, tus PIT, las fichas y metas de tus clientes, tus informes y tus
exportes. La versión anterior queda respaldada en `~/.config/ghl-marketing/respaldos/`.

**Cómo se protege la descarga:** el archivo se comprueba contra su huella publicada (sha256) antes de instalar nada.

Si clonaste con git, `actualizar` hace `git pull`.

Al pasar a la 1.2 o posterior: para el embudo y los chats sin respuesta, agrega a cada PIT los 4 permisos de CRM
(`docs/PIT.md`; el token no cambia). Sin ellos, todo lo demás sigue funcionando.

---

*Hecho por **Escala+**. Código visible, **no de código abierto**: su uso requiere autorización de Escala+. Ver [`LICENCIA.md`](LICENCIA.md).*

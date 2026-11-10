# Cómo sacar el PIT de una subcuenta (5 minutos, una vez por subcuenta)

El **PIT** (*Private Integration Token*) es una clave que GoHighLevel da a cada subcuenta. Con ella, el agente
hace por API lo que tú harías en la pantalla de GHL. **Es como una contraseña: no la pegues en chats ni en
documentos.** Se guarda solo en tu computadora con `python3 ghl.py conectar`.

## 1. Crear el token

1. Entra a GHL y **cámbiate a la subcuenta del cliente** (no a la vista de agencia). Un token de agencia no
   sirve: GHL lo rechaza con `authClass type is not allowed`.
2. **Settings → Private Integrations → Create new Integration**.
3. Nombre: `agente-marketing` (o el que quieras). Descripción: opcional.
4. **Scopes (permisos):** marca todos estos. Es mejor que sobren a que falten: si falta uno, el agente se
   frena a medio trabajo y hay que volver a editar el token.

| Para qué | Scopes |
|---|---|
| Datos de la subcuenta y usuarios | `locations.readonly` · `users.readonly` |
| Redes sociales (Social Planner) | `socialplanner/account.readonly` · `socialplanner/post.readonly` · `socialplanner/post.write` · `socialplanner/category.readonly` · `socialplanner/tag.readonly` · `socialplanner/statistics.readonly` · `socialplanner/csv.readonly` · `socialplanner/csv.write` |
| Imágenes y videos | `medias.readonly` · `medias.write` |
| Anuncios de Meta (Ad Manager) | `adPublishing.readonly` · `adPublishing.write` |
| Blogs | `blogs/list.readonly` · `blogs/posts.readonly` · `blogs/author.readonly` · `blogs/category.readonly` · `blogs/check-slug.readonly` · `blogs/post.write` · `blogs/post-update.write` |
| Correos | `emails/builder.readonly` · `emails/schedule.readonly` |
| Enlaces y marca | `links.readonly` · `brand-boards/design-kit.readonly` |
| CRM: de anuncio a venta y chats sin respuesta (solo lectura) | `contacts.readonly` · `opportunities.readonly` · `conversations.readonly` · `conversations/message.readonly` |

   Los permisos de CRM dejan **leer** contactos, oportunidades y conversaciones. La herramienta solo saca cifras
   (cuántos leads, de dónde, cuántas ventas) y ligas a los chats; nunca muestra nombres, teléfonos ni mensajes. No
   marques permisos de escritura del CRM: esta herramienta no los usa.

   Si el buscador de scopes no muestra alguno con ese nombre exacto, busca la palabra (`socialplanner`,
   `adPublishing`, `blogs`…) y marca todo lo de lectura y escritura de esa familia.
5. **Create** → copia el token (empieza con `pit-`). GHL solo lo enseña una vez; si lo pierdes, se crea otro.

**Agregar un permiso después:** Settings → Private Integrations → tu token → ⋮ → **Edit** → Next → marca el scope →
**Update** → Confirm. El token **no cambia**, no hay que volver a conectarlo.

## 2. El locationId (o simplemente la URL)

Es el código de la subcuenta. **Lo más fácil: copia la URL completa** de la barra de direcciones estando dentro de
la subcuenta y pégala cuando `conectar` te la pida; la herramienta saca el código sola.

```
https://app.gohighlevel.com/v2/location/AbCdEf123456XyZ/dashboard
                                        └──── locationId ────┘
```

(El campo copiable de Settings a veces corta la primera letra; la URL no falla.)

## 3. Conectarlo

```bash
python3 ghl.py conectar
```

Son 3 preguntas: el PIT (no se ve al pegarlo), la URL o el locationId, y quién eres de los usuarios de la
subcuenta. Dónde queda el PIT:

| Sistema | Dónde | Cómo verlo o borrarlo |
|---|---|---|
| **Mac** | Llavero (cifrado), servicio `ghl-marketing` | App «Acceso a Llaveros» → buscar `ghl-marketing` |
| **Linux** con `secret-tool` | Llavero del escritorio (GNOME/KDE) | `secret-tool lookup service ghl-marketing account <alias>` |
| **Windows** u otro | `~/.config/ghl-marketing/cuentas.json`, solo tu usuario lo lee | Borrar la entrada con `cuentas --quitar` |

**Con Codex** (o cualquier agente que solo deja escribir dentro de la carpeta del proyecto) todo se guarda en
`.ghl-datos/` dentro de esta carpeta. Está fuera de git y las actualizaciones no la tocan. **Si compartes la carpeta,
bórrala antes**: ahí quedan tus PIT.

**Si Codex dice «Sin internet en este entorno»:** cuando te pida aprobación para correr el comando, dale **Aprobar**.
Si te ofrece no volver a preguntar para comandos que empiecen con `python ghl.py`, elígelo. No hace falta tocar
ninguna configuración.

Al terminar, `conectar` corre el diagnóstico solo (puedes repetirlo con `python3 ghl.py diagnostico`). Cada ✅ es algo que el agente ya puede hacer. Cada ❌ es un scope que falta (vuelve al paso de agregar permisos).
🟡 = el permiso está, pero falta conectar algo en GHL (por ejemplo, Facebook en Ad Manager).

## 4. Varias subcuentas

Corre `conectar` una vez por cliente. Después:

```bash
python3 ghl.py cuentas                       # ★ = la que se usa por defecto
python3 ghl.py cuentas --usar tienda-sol  # cambiar la de por defecto
python3 ghl.py redes metricas --cuenta clinica-norte   # usar otra solo en un comando
python3 ghl.py cuentas --quitar clinica-norte         # desconectarla (borra su PIT del Llavero)
python3 ghl.py agencia resumen                   # todas a la vez
```

## 5. Para anuncios, además

La API de anuncios lee la cuenta publicitaria que la subcuenta tiene conectada:

1. **Marketing → Ad Manager**: conectar Facebook (la página y la cuenta publicitaria del cliente). Lo ideal es
   que lo conecte el **propio cliente con su Facebook**: Meta da los permisos por persona, y mezclar usuarios
   puede quitarle páginas a otro cliente.
2. Para **leer reportes** de campañas creadas en Meta Ads Manager: Settings → Integrations → Facebook →
   Manage → **Settings** → pestaña **Ad Account** → elegir la cuenta. Se guarda al elegirla.
3. `python3 ghl.py ads verificar` debe quedar todo en ✅.

## Si algo sale mal

| Mensaje | Qué pasa |
|---|---|
| `The token is not authorized for this scope` | Falta un scope: agrégalo (el token no cambia) |
| `This location is not accessible from this token` | El PIT es de otra subcuenta o el locationId está mal |
| `Invalid JWT` / 401 a secas | El token se borró o está mal copiado: crea otro y `conectar` de nuevo |
| `Access Token not found` (anuncios) | La subcuenta no tiene Facebook conectado en Ad Manager |
| `Ad Account not found` (reportes) | Falta elegir la cuenta en Integrations → Facebook → Settings → Ad Account |

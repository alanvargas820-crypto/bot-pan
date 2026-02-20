# 🤖 AnonBot — Telegram SaaS Bot Premium

Bot profesional multi-grupo con modo anónimo, VIP, anti-spam, anti-fake, roles, logs puente, temas/tópicos, y auto-limpieza.

---

## 🚀 Deploy

### 1. BotFather
- `/newbot` → copia el token
- **`/setprivacy` → Disable** (obligatorio)

### 2. GitHub
Sube todos los archivos a la raíz del repo (sin carpetas).

### 3. Railway
- New Project → Deploy from GitHub
- Variables: `BOT_TOKEN` ✅, `OWNER_ID` ✅, `LOG_GROUP_ID` (opcional)

### 4. Grupo
- Agrega el bot como **admin** (eliminar mensajes, restringir, banear)
- En el panel privado: 📊 Mis Grupos → ➕ Vincular grupo → escribe en el grupo

---

## 📖 Panel

Abre chat privado → `/start`

| Botón | Función |
|---|---|
| 📊 Mis Grupos | Ver/vincular/desvincular TUS grupos |
| ⚙️ Nombre del Bot | Nombre visual por grupo |
| 👻 Modo Anónimo | ON/OFF por grupo |
| ⭐ VIP | Agregar/quitar exentos del anónimo |
| 🛡️ Anti-Fake | Cuentas nuevas/falsas |
| 🚨 Anti-Spam | Flood, links, repetición |
| 📢 Logs | Grupo destino + eventos |
| 🧹 Limpieza | Kick cuentas eliminadas |
| 👑 Roles | Owner/Admin/Mod |
| 💬 Temas | Topic fijo para anónimo |
| ⏱ Auto-Limpieza | Borrar msgs del bot tras X tiempo |

---

## 🔑 Vincular grupo (sin comandos)

1. Panel → 📊 Mis Grupos → ➕ Vincular grupo
2. Escribe cualquier mensaje en el grupo
3. El bot valida que eres admin y lo vincula
4. Solo TÚ ves ese grupo en tu panel

---

## 💬 Temas (Topics)

- Si el grupo tiene foro/temas, puedes fijar un topic para mensajes anónimos
- Si no fijas ninguno, el bot responde en el mismo tema donde escribió el usuario

---

## ⏱ Auto-Limpieza

- Borra mensajes anónimos del bot después de: 15min / 1h / 6h / 24h / Off
- Job queue ejecuta cada 5 minutos

---

## ⚠️ Limitaciones reales de Telegram

| Limitación | Detalle |
|---|---|
| Fecha creación cuenta | API no la expone — heurísticas |
| Username del bot | No cambiable — solo nombre visual |
| Listar miembros | API no permite — solo detecta en eventos |
| Privacy mode | Debe estar en Disable |

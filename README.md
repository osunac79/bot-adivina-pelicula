# 🎬 Adivina la Película — bot de Mastodon

Un bot-juego: cada día publica una pista nueva (hasta **7**) de una película misteriosa.
Quien la adivina gana puntos (**7 si acierta con la pista 1 … 1 con la pista 7**).
Al acertar, o al acabar la pista 7, el bot revela **título, datos y portada** 🖼️.

Funciona **sin servidor**: todo corre en GitHub Actions y el estado se guarda en `state.json`.

## ✨ Qué incluye
- 🔤 Título en huecos (`_ _ _`) + letras reveladas poco a poco (0 → 5 según la pista)
- 🔍 7 pistas diarias: huecos · género · época y país · dirección · reparto · eslogan · sinopsis (sin spoilers: el título sale tapado)
- 🏆 Ranking semanal, mensual y total · 🔥 rachas con bonus · 📊 resumen semanal · 🏅 campeones del mes
- 🎃🎄 Temáticas: clásicos, cine español, ciencia ficción, animación, **modo difícil** (+2 pts), especial terror/monstruos (Halloween) y Navidad
- 🤫 Respuestas por mención privada: el bot contesta en privado a cada intento
- 🤖 Comandos: `!pista` · `!ranking` · `!racha` · `!ayuda`
- 🔠 Tolera tildes, mayúsculas, artículos y pequeñas erratas; no confunde "Toy Story 2" con "Toy Story 3"
- 🚦 Máximo 5 intentos por persona y pista

## 🚀 Puesta en marcha (≈15 min)

### 1. Cuenta del bot en Mastodon
1. Crea (o usa) la cuenta del bot y márcala como **bot** en *Preferencias → Perfil*.
2. *Preferencias → Desarrollo → Nueva aplicación*. Nombre: `Adivina la Película`.
   Permisos (scopes): **read** y **write** (`read:notifications`, `write:statuses`, `write:media`).
3. Guarda el **token de acceso** ("Tu token de acceso").

### 2. Clave de TMDB (gratis, para datos y portadas)
Regístrate en <https://www.themoviedb.org/settings/api> y copia la **clave de API (v3)**.

### 3. Repositorio en GitHub
1. Crea un repositorio nuevo (**público** recomendado: los minutos de Actions son ilimitados).
2. Sube todos los archivos de este proyecto.
   📱 *Desde el móvil:* si no puedes subir la carpeta oculta `.github`, usa **Add file → Create new file** y escribe el nombre
   `.github/workflows/daily.yml` (las barras crean las carpetas); pega el contenido. Repite con `replies.yml` y `weekly.yml`.
3. *Settings → Secrets and variables → Actions → New repository secret*, crea **tres** secretos:

| Nombre | Valor |
|---|---|
| `MASTODON_API_BASE_URL` | La URL de tu instancia, ej. `https://mastodon.social` |
| `MASTODON_ACCESS_TOKEN` | El token del paso 1 |
| `TMDB_API_KEY` | La clave del paso 2 |

4. *Settings → Actions → General → Workflow permissions* → **Read and write permissions** → Save.

### 4. Primer arranque
1. Pestaña **Actions** → *Leer respuestas* → **Run workflow** (se inicializa).
2. *Pista diaria* → **Run workflow** → marca `force` → ¡primera ronda publicada! 🎉

A partir de ahí es automático:

| Workflow | Cuándo | Qué hace |
|---|---|---|
| Pista diaria | cada día 09:00 (Madrid, invierno) | publica la pista; el día 8 revela y abre ronda nueva |
| Leer respuestas | cada 15 min | corrige respuestas y comandos |
| Resumen semanal | domingos por la tarde | ranking semanal y reinicio |

> GitHub puede retrasar los cron unos minutos: es normal.
> Si el repo es **privado**, cambia `*/15` por `*/30` en `replies.yml` para no gastar los minutos gratis.

## 🎮 Reglas (para tu perfil o toot fijado)
- Una película misteriosa por ronda, una pista nueva cada día (7 en total).
- Responde al toot del bot con el título, ¡mejor en **mención privada**! 🤫
- Cuanto antes aciertes, más puntos (7 → 1). Rondas seguidas acertadas = bonus de racha (+1 con 3, +2 con 5).
- Si nadie acierta, el día 8 se revela la solución.

## 🛠️ Personalizar
- **Temáticas y rotación:** `themes.py`
- **Puntos, intentos, hashtags, límite de caracteres:** `config.py` (`MAX_CHARS` si tu instancia admite más de 500)
- **Textos y emoticonos:** `messages.py`
- **Hora de publicación:** el `cron` de `.github/workflows/daily.yml` (en UTC)

## 🧪 Probar sin publicar
```bash
pip install -r requirements.txt
python -m unittest discover -s tests          # tests con Mastodon y TMDB simulados
export TMDB_API_KEY=tu_clave
python bot.py daily --dry-run --force          # imprime el toot en lugar de publicarlo
python bot.py status                           # estado actual
```

## 📁 Estructura
```
bot.py        motor: ronda diaria, respuestas, resumen semanal
game.py       normalizar respuestas, máscara de letras, pistas, puntos
tmdb.py       películas y portadas (TMDB)
social.py     capa sobre Mastodon.py (con modo --dry-run)
messages.py   todos los textos con emoticonos
themes.py     temáticas y rotación
state.json    estado del juego (lo actualiza el bot)
tests/        pruebas automáticas
```

Datos de películas e imágenes: © TMDB. *Este producto usa la API de TMDB pero no está avalado ni certificado por TMDB.*

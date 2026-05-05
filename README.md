<div align="center">

# WallBot

**Bot de Telegram que monitoriza Wallapop y avisa cuando aparecen artículos nuevos o bajan de precio.**

[![Docker Pulls](https://img.shields.io/docker/pulls/nemesbak/wallbot)](https://hub.docker.com/r/nemesbak/wallbot)
[![Docker Image Size](https://img.shields.io/docker/image-size/nemesbak/wallbot/latest)](https://hub.docker.com/r/nemesbak/wallbot)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> Basado en [z0r3f/wallbot](https://github.com/z0r3f/wallbot) — proyecto original de [@z0r3f](https://github.com/z0r3f).
> Este fork reescribe y amplía el bot con nuevas funcionalidades manteniendo la idea original.

</div>

---

## Índice

- [Características](#características)
- [Despliegue](#despliegue)
  - [Opción A — Imagen Docker Hub (recomendado)](#opción-a--imagen-docker-hub-recomendado)
  - [Opción B — Clonar y construir](#opción-b--clonar-y-construir)
- [Uso](#uso)
- [Filtros](#filtros)
- [Tests](#tests)
- [Créditos](#créditos)

---

## Características

<details>
<summary><strong>Heredadas del proyecto original</strong></summary>

- Monitorización periódica de búsquedas en Wallapop
- Notificaciones de artículos nuevos
- Notificaciones de bajada de precio
- Filtros por precio mínimo/máximo y distancia

</details>

<details open>
<summary><strong>Añadidas en este fork</strong></summary>

| Funcionalidad | Descripción |
|---|---|
| `/search` | Búsqueda inmediata con paginación inline (sin crear alerta) |
| Filtro `10%` | Avisa solo si el precio baja un % mínimo configurable |
| Auto-detección de filtros | `/add ps5 200-350 50km` — sin necesidad de coma |
| Descripciones en notificaciones | Muestra el texto del anuncio truncado |
| Fotos en notificaciones | Envía la imagen del artículo si está disponible |
| Menú de comandos Telegram | Registro de comandos con descripciones (botón `≡`) |
| Teclado persistente | Botones de acceso rápido en la parte inferior del chat |
| Pausa/Reanuda alertas | Sin necesidad de borrar y recrear |
| `/stats` | Estadísticas de alertas e ítems encontrados |
| `/clear` | Elimina todas las alertas con confirmación inline |
| Notificación de reinicio | Avisa a los usuarios activos cuando el bot arranca |
| Reconexión automática | Backoff exponencial ante errores de Telegram |
| Logs por stdout | Compatible con `docker logs` |
| Python 3.11 | Actualizado desde Python 3.8 |
| Suite de tests | 97 tests unitarios e integración con pytest |

</details>

---

## Despliegue

### Requisito previo — Obtener el token de Telegram

1. Abre Telegram y habla con [@BotFather](https://t.me/BotFather)
2. Envía `/newbot` y sigue los pasos
3. Copia el token que te da (formato `123456789:ABC-...`)

---

### Opción A — Imagen Docker Hub (recomendado)

Sin necesidad de clonar el repo. Solo necesitas un `docker-compose.yml` y el token.

**1. Crea la carpeta del proyecto y el fichero de compose:**

```bash
mkdir wallbot && cd wallbot
```

**2. Crea `docker-compose.yml`:**

```yaml
services:
  wallbot:
    image: nemesbak/wallbot:latest
    container_name: wallbot
    restart: unless-stopped
    environment:
      - BOT_TOKEN=tu_token_aqui
    volumes:
      - ./data:/data
      - ./logs:/logs
```

> También puedes usar un fichero `.env` en lugar de escribir el token directamente:
>
> ```yaml
> environment:
>   - BOT_TOKEN=${BOT_TOKEN}
> ```
>
> Y crear `.env` con:
> ```
> BOT_TOKEN=tu_token_aqui
> ```

**3. Arrancar:**

```bash
docker compose up -d
docker logs -f wallbot
```

**4. Actualizar a la última versión:**

```bash
docker compose pull
docker compose up -d
```

---

### Opción B — Clonar y construir

Si quieres modificar el código o ejecutar los tests.

**1. Clonar y configurar:**

```bash
git clone https://github.com/nemesbak/wallbot.git
cd wallbot
cp .env.example .env
# Edita .env y pon tu token
```

**2. Contenido del `.env`:**

```env
BOT_TOKEN=tu_token_aqui
```

**3. Construir y arrancar:**

```bash
docker compose up -d --build
docker logs -f wallbot
```

**4. Parar / reiniciar:**

```bash
docker compose down        # parar y eliminar el contenedor
docker compose restart     # reiniciar sin reconstruir
```

---

## Uso

### Comandos principales

| Comando | Descripción |
|---|---|
| `/search ps5` | Busca ahora en Wallapop con paginación inline |
| `/add ps5` | Crea una alerta y monitoriza cada 5 min |
| `/lis` | Lista y gestiona tus alertas (pausar/reanudar/borrar) |
| `/stats` | Estadísticas de alertas e ítems encontrados |
| `/del ps5` | Elimina una alerta específica |
| `/clear` | Elimina todas las alertas con confirmación |
| `/help` | Referencia rápida de comandos |

El bot también muestra un **teclado persistente** con los botones más usados y registra todos los comandos en el menú `≡` de Telegram.

---

## Filtros

Los filtros se escriben después del término de búsqueda, separados por espacios:

```
/add ps5 200-350          → precio entre 200 € y 350 €
/add ps5 -350             → hasta 350 €
/add ps5 200-             → desde 200 €
/add ps5 50km             → radio de 50 km
/add ps5 10%              → avisa solo si baja ≥ 10 %
/add ps5 200-350 50km 10% → todo combinado
```

También se puede usar coma como separador explícito: `/add ps5,200-350 50km`.

Los filtros funcionan igual en `/search` que en `/add`.

---

## Tests

```bash
docker compose run --rm wallbot sh -c "pip install pytest -q && python -m pytest tests/ -v"
```

97 tests cubren: filtros, base de datos, monitor, cliente API y notificaciones.

---

## Créditos

- **Proyecto original**: [z0r3f/wallbot](https://github.com/z0r3f/wallbot) por [@z0r3f](https://github.com/z0r3f) — licencia MIT
- **Fork y ampliación**: [@nemesbak](https://github.com/nemesbak)

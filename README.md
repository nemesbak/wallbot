# WallBot 🤖

Bot de Telegram que monitoriza Wallapop y avisa cuando aparecen artículos nuevos o bajan de precio.

> **Basado en [z0r3f/wallbot](https://github.com/z0r3f/wallbot)** — proyecto original de [@z0r3f](https://github.com/z0r3f).  
> Este fork reescribe y amplía el bot con nuevas funcionalidades manteniendo la idea original.

---

## Características

### Heredadas del proyecto original
- Monitorización periódica de búsquedas en Wallapop
- Notificaciones de artículos nuevos
- Notificaciones de bajada de precio
- Filtros por precio mínimo/máximo y distancia

### Añadidas en este fork
| Funcionalidad | Descripción |
|---|---|
| `/search` | Búsqueda inmediata con paginación inline (sin alertas) |
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

---

## Despliegue rápido

### Requisitos
- Docker y Docker Compose

### 1. Clonar y configurar
```bash
git clone https://github.com/nemesbak/wallbot.git
cd wallbot
cp .env.example .env
# Edita .env y pon tu token de Telegram
```

### 2. Obtener el token
1. Habla con [@BotFather](https://t.me/BotFather) en Telegram
2. Usa `/newbot` y sigue los pasos
3. Copia el token y pégalo en `.env`

### 3. Arrancar
```bash
docker compose up -d
docker logs -f wallbot
```

---

## Uso

### Comandos principales

| Comando | Descripción |
|---|---|
| `/search ps5` | Busca ahora en Wallapop con paginación |
| `/add ps5` | Crea una alerta y monitoriza cada 5 min |
| `/lis` | Lista y gestiona tus alertas (pausar/borrar) |
| `/stats` | Estadísticas de alertas e ítems encontrados |
| `/del ps5` | Elimina una alerta específica |
| `/clear` | Elimina todas las alertas |
| `/help` | Referencia rápida |

### Filtros

Los filtros se escriben después del término, separados por espacios:

```
/add ps5 200-350       → precio entre 200€ y 350€
/add ps5 -350          → hasta 350€
/add ps5 200-          → desde 200€
/add ps5 50km          → radio de 50 km
/add ps5 10%           → avisa solo si baja ≥10%
/add ps5 200-350 50km 10%   → todo combinado
```

También funciona con coma como separador explícito: `/add ps5,200-350 50km`.

---

## Ejecutar los tests

```bash
docker compose run --rm wallbot sh -c "pip install pytest -q && python -m pytest tests/ -v"
```

---

## Imagen Docker

```bash
docker pull nemesbak/wallbot:latest
```

---

## Créditos

- **Proyecto original**: [z0r3f/wallbot](https://github.com/z0r3f/wallbot) por [@z0r3f](https://github.com/z0r3f) — licencia MIT
- **Fork**: [@nemesbak](https://github.com/nemesbak)

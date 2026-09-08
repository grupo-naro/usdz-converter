# usdz-converter

Servicio HTTP que convierte modelos **GLB/GLTF → USDZ** con
[`usd_from_gltf`](https://github.com/google/usd_from_gltf) de Google
(sobre Pixar USD). Lo usa el panel admin de la tienda para generar la
versión iOS (AR Quick Look) de cada modelo 3D: el `.glb` da AR en
Android, el `.usdz` da AR en iPhone.

Corre **fuera de Vercel** (necesita las librerías nativas de USD). Esta
carpeta se despliega en un VPS / servidor propio.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | `200 ok` — para healthchecks. |
| `POST` | `/convert` | Body = bytes del `.glb`. Header `X-Auth-Token: <CONVERTER_TOKEN>`. Devuelve los bytes del `.usdz` (`Content-Type: model/vnd.usdz+zip`). |

Errores: `401` token inválido · `413` archivo > `CONVERTER_MAX_MB` ·
`422` la conversión falló (el body trae el stderr) · `504` timeout.

## Variables de entorno

| Var | Default | |
|---|---|---|
| `CONVERTER_TOKEN` | — | **Obligatoria.** Secreto compartido con la app (`USDZ_CONVERTER_TOKEN`). |
| `CONVERTER_PORT` | `8080` | Puerto HTTP. |
| `CONVERTER_MAX_MB` | `64` | Tamaño máximo del `.glb`. |
| `CONVERTER_TIMEOUT` | `180` | Segundos para `usd_from_gltf`. |

## Desplegar en el VPS

```bash
# 1. Copiar esta carpeta al servidor, entrar en ella.
cd usdz-converter

# 2. Build.
docker build -t usdz-converter .

# 3. Run (elegí un token largo y aleatorio).
docker run -d --name usdz-converter --restart unless-stopped \
  -p 127.0.0.1:8080:8080 \
  -e CONVERTER_TOKEN="pegá-acá-un-secreto-largo" \
  usdz-converter

# 4. Exponer por HTTPS con un reverse proxy (Caddy / nginx) apuntando
#    a 127.0.0.1:8080, con un dominio, p. ej. https://usdz.tudominio.com
```

Ejemplo de bloque Caddy:

```
usdz.tudominio.com {
    reverse_proxy 127.0.0.1:8080
}
```

## Probar

```bash
curl -fsS https://usdz.tudominio.com/health        # -> ok

curl -fsS -X POST https://usdz.tudominio.com/convert \
  -H "X-Auth-Token: <CONVERTER_TOKEN>" \
  --data-binary @modelo.glb \
  -o modelo.usdz

# Abrí modelo.usdz en un Mac (Quick Look) para verificar materiales.
```

## Configurar la app

En las env vars del deploy de la tienda:

```
USDZ_CONVERTER_URL="https://usdz.tudominio.com"
USDZ_CONVERTER_TOKEN="el-mismo-secreto-que-CONVERTER_TOKEN"
```

Sin `USDZ_CONVERTER_URL`, el panel guarda sólo el `.glb` (AR sólo en
Android) y lo avisa.

## Si el build de la imagen falla

`leon/gltf-to-usdz` compila USD; si la imagen base se rompe con el
tiempo, alternativas: buildear `usd_from_gltf` desde su repo, o generar
el `.usdz` a mano con **Reality Converter** (macOS) y subirlo desde el
panel (el campo admite reemplazo manual).

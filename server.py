#!/usr/bin/env python3
"""Servidor HTTP mínimo que convierte GLB/GLTF -> USDZ con `usd_from_gltf`.

Sólo stdlib. Endpoints:

  GET  /health   -> 200 "ok"
  POST /convert  -> recibe los bytes del .glb en el body, devuelve los
                    bytes del .usdz (Content-Type: model/vnd.usdz+zip).
                    Requiere el header `X-Auth-Token` == $CONVERTER_TOKEN.

Variables de entorno:
  CONVERTER_TOKEN  (obligatoria) secreto compartido con la app.
  CONVERTER_PORT   (opcional, default 8080)
  CONVERTER_MAX_MB (opcional, default 64) tamaño máximo del body.
  CONVERTER_TIMEOUT (opcional, default 180) segundos para usd_from_gltf.
"""
import os
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("CONVERTER_TOKEN", "")
PORT = int(os.environ.get("CONVERTER_PORT", "8080"))
MAX_BYTES = int(os.environ.get("CONVERTER_MAX_MB", "64")) * 1024 * 1024
TIMEOUT = int(os.environ.get("CONVERTER_TIMEOUT", "180"))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body=b"", content_type="text/plain; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        # En los caminos de rechazo (401/413/400/404) hacemos return sin leer el
        # body del request; con HTTP/1.1 keep-alive esos bytes sin leer corrompen
        # el request siguiente en la conexión upstream que reusa el tunnel.
        # Forzar el cierre de la conexión en cualquier error lo evita.
        if code >= 400:
            self.close_connection = True
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # una línea por request, a stdout
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, "ok")
        else:
            self._send(404, "not found")

    def do_POST(self):
        if self.path != "/convert":
            self._send(404, "not found")
            return

        if not TOKEN:
            self._send(500, "CONVERTER_TOKEN no configurado en el servicio")
            return
        if self.headers.get("X-Auth-Token", "") != TOKEN:
            self._send(401, "token inválido")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, "Content-Length inválido")
            return
        if length <= 0:
            self._send(400, "body vacío")
            return
        if length > MAX_BYTES:
            self._send(413, "archivo demasiado grande")
            return

        glb = self.rfile.read(length)

        with tempfile.TemporaryDirectory(dir="/work") as tmp:
            in_path = os.path.join(tmp, "input.glb")
            out_path = os.path.join(tmp, "output.usdz")
            with open(in_path, "wb") as fh:
                fh.write(glb)

            try:
                proc = subprocess.run(
                    ["usd_from_gltf", in_path, out_path],
                    capture_output=True,
                    timeout=TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                self._send(504, "usd_from_gltf excedió el tiempo límite")
                return

            if proc.returncode != 0 or not os.path.exists(out_path):
                detail = (proc.stderr or proc.stdout or b"").decode(
                    "utf-8", "replace"
                )[:2000]
                self._send(422, "conversión falló:\n" + detail)
                return

            with open(out_path, "rb") as fh:
                usdz = fh.read()

        self._send(200, usdz, "model/vnd.usdz+zip")


def main():
    if not TOKEN:
        print(
            "AVISO: CONVERTER_TOKEN no está seteado — /convert rechazará todo.",
            flush=True,
        )
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("usdz-converter escuchando en :%d" % PORT, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

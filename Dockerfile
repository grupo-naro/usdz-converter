# Servicio de conversión GLB/GLTF -> USDZ.
#
# Base: imagen comunitaria que empaqueta `usd_from_gltf` de Google
# (https://github.com/google/usd_from_gltf) sobre Pixar USD. Sobre eso
# montamos un servidor HTTP mínimo (stdlib de Python, sin dependencias)
# que expone `POST /convert`.
#
# La base trae `usd_from_gltf` en el PATH y Python 3.
FROM leon/usd-from-gltf:latest

# Anula el ENTRYPOINT de la base (que es el binario `usd_from_gltf`).
ENTRYPOINT []

COPY server.py /app/server.py

# Directorio de trabajo para los archivos temporales de cada conversión.
WORKDIR /work

# Puerto HTTP del servicio. El token se pasa en runtime:
#   docker run -e CONVERTER_TOKEN=... -p 8080:8080 usdz-converter
ENV CONVERTER_PORT=8080
EXPOSE 8080

CMD ["python3", "/app/server.py"]

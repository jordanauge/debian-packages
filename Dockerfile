FROM debian:forky-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential debhelper devscripts gnupg lintian ca-certificates \
    python3 python3-yaml curl e2fsprogs systemd debconf-utils adduser \
    dh-python pybuild-plugin-pyproject python3-all python3-setuptools \
    python3-setuptools-scm python3-wheel python3-requests \
    python3-hatchling python3-httpx python3-typer python3-rich python3-pydantic \
    python3-platformdirs python3-zeroconf python3-websockets python3-textual \
    python3-tomli-w python3-pytest python3-respx \
    && rm -r /var/lib/apt/lists
WORKDIR /build

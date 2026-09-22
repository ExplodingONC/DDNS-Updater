# -- builder stage --
FROM python:3.14-slim AS builder

COPY --from=astral/uv:latest /uv /usr/local/bin/uv

ENV UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/

RUN uv build

# -- runtime stage --
FROM python:3.14-slim

ENV UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

RUN useradd --create-home ddns-updater

COPY --from=astral/uv:latest /uv /usr/local/bin/uv
COPY --from=builder /app/dist/*.whl /tmp/
RUN printf 'Types: deb\nURIs: https://mirrors.tuna.tsinghua.edu.cn/debian\nSuites: trixie trixie-updates\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.pgp\n\nTypes: deb\nURIs: https://mirrors.tuna.tsinghua.edu.cn/debian-security\nSuites: trixie-security\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.pgp\n' > /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends iproute2 \
    && rm -rf /var/lib/apt/lists/* \
    && uv pip install --system --break-system-packages --no-cache /tmp/*.whl \
    && rm -rf /tmp/*.whl \
    && mkdir -p /etc/ddns_updater /var/log/ddns_updater \
    && chown ddns-updater:ddns-updater /var/log/ddns_updater

USER ddns-updater
WORKDIR /home/ddns-updater

ENTRYPOINT ["ddns-updater"]

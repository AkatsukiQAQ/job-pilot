# Mita JobPilot runtime image. Same uv version as the developer machine; bump all three
# (local, this file, CI) together and re-run `uv lock`.
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.10.7 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project
COPY src ./src
RUN uv sync --locked

FROM python:3.12-slim
RUN groupadd --gid 10001 jobpilot && useradd --uid 10001 --gid 10001 --create-home jobpilot
WORKDIR /app
COPY --from=builder --chown=jobpilot:jobpilot /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    JOBPILOT_DATA_DIR=/data \
    JOBPILOT_SECRET_BACKEND=fernet \
    JOBPILOT_HOST=0.0.0.0
VOLUME ["/data"]
USER jobpilot
HEALTHCHECK --interval=60s --timeout=10s CMD ["jobpilot", "doctor", "--quiet"]
ENTRYPOINT ["jobpilot"]
CMD ["doctor"]

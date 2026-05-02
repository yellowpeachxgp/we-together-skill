# we-together Dockerfile（多阶段）
# - builder: 安装依赖 + 拷源码
# - runtime: 只留 venv + 项目文件

FROM python:3.13-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
COPY db ./db
COPY SKILL.md ./SKILL.md
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -U pip \
    && /opt/venv/bin/pip install --no-cache-dir .


FROM python:3.13-slim AS runtime
LABEL org.opencontainers.image.title="we-together-skill"
LABEL org.opencontainers.image.description="Skill-first social graph runtime"
LABEL org.opencontainers.image.version="0.9.0"

ENV PATH="/opt/venv/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build /app
WORKDIR /app

# 默认入口 = we-together CLI。子命令由 CMD / 运行时参数决定
ENTRYPOINT ["we-together"]
CMD ["version"]

# 多架构 Dockerfile —— 支持 x86 (L1/L2) 和 ARM (L3)
ARG TARGETARCH=amd64
FROM --platform=linux/${TARGETARCH} python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ARM 架构额外安装（在 L3 昇腾机上用）
ARG TARGETARCH
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        echo "ARM64 detected — install Ascend/CANN packages when available"; \
    fi

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

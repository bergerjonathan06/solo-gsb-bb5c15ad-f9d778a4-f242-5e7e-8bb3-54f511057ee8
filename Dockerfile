FROM python:3.11-slim

# 不生成 .pyc、实时刷新日志
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖，利用层缓存
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码与静态资源
COPY app ./app
COPY static ./static

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz').status==200 else 1)"

# 依赖与初始化均在镜像构建时完成，容器启动即提供服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

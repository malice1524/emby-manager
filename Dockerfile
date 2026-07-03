FROM python:3.12-alpine

WORKDIR /app

# 后端依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 后端代码
COPY backend/app/ ./app/

# 前端静态文件（兼容 local dev 和 Docker 两种路径）
COPY frontend/index.html ./static/
COPY frontend/lib/ ./static/lib/

EXPOSE 8000

ENV TZ=Asia/Shanghai

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-alpine

WORKDIR /app

# 后端依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 后端代码
COPY backend/app/ ./app/

# 前端静态文件
COPY static/index.html ./static/
COPY static/lib/ ./static/lib/
COPY static/favicon.png ./static/ 2>/dev/null || true

EXPOSE 8000

ENV TZ=Asia/Shanghai

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

  GNU nano 6.2                     Dockerfile                               # 📌 Base: slim Python 3.10
FROM python:3.10-slim

# 📁 Set working directory
WORKDIR /app

# 🔁 Optional: Break cache for git clone (every build is fresh)
ARG CACHEBUST=1

# 🧰 Install git + build tools
RUN apt-get update && \
    apt-get install -y git build-essential && \
    apt-get clean

# 🧬 Clone specific branch from backend repo (site)
RUN git clone --branch site --single-branch https://github.com/BobbyAxelrod>
# 🧬 Clone Microsoft GraphRAG repo
RUN git clone https://github.com/microsoft/graphrag.git /tmp/graphrag

# ✅ Install GraphRAG as a module
RUN pip install /tmp/graphrag

# 📦 Install backend dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Expose FastAPI port
EXPOSE 8000

# 🚀 Start FastAPI app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]




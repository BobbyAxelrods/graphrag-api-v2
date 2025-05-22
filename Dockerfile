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
# RUN git clone --branch site --single-branch https://github.com/BobbyAxelr>RUN git clone https://github.com/microsoft/graphrag.git /tmp/graphrag

# ✅ Install GraphRAG as a module
RUN pip install /tmp/graphrag

COPY . .

# 📦 Install backend dependencies
RUN pip install -r requirements.txt

# ✅ Expose FastAPI port
EXPOSE 8000

# 🚀 Start FastAPI app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

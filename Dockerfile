# # 📌 Base: slim Python 3.10
# FROM python:3.10-slim

# # 📁 Set working directory
# WORKDIR /app

# # 🧰 Install git + build tools
# RUN apt-get update && \
#     apt-get install -y git build-essential && \
#     apt-get clean

# # 🧬 Clone your backend repo
# RUN git clone https://github.com/BobbyAxelrods/graphrag-api-v2.git .

# # 🧬 Clone Microsoft GraphRAG repo
# RUN git clone https://github.com/microsoft/graphrag.git /tmp/graphrag

# # ✅ Install graphrag as local module
# RUN pip install /tmp/graphrag

# # 📦 Install backend dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # ✅ Expose FastAPI port
# EXPOSE 8000

# # 🚀 Start FastAPI app
# CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]


# 📌 Base: slim Python 3.10
FROM python:3.10-slim

# 📁 Set working directory
WORKDIR /app

# 🧰 Install git + build tools
RUN apt-get update && \
    apt-get install -y git build-essential && \
    apt-get clean

# 🧬 Clone specific branch from backend repo
RUN git clone --branch site --single-branch https://github.com/BobbyAxelrods/graphrag-api-v2.git .

# 🧬 Clone Microsoft GraphRAG repo
RUN git clone https://github.com/microsoft/graphrag.git /tmp/graphrag

# ✅ Install graphrag as local module
RUN pip install /tmp/graphrag

# 📦 Install backend dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Expose FastAPI port
EXPOSE 8000

# 🚀 Start FastAPI app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

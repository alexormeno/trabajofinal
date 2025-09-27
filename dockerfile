# FROM python:3.8-slim-buster
FROM python:3.11-slim

#RUN apt-get update && apt-get install -y python3-distutils python3-apt && rm -rf /var/lib/apt/lists/*

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    libsqlite3-dev \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# RUN mkdir wd
# WORKDIR wd
RUN mkdir -p /home/app/app/utils/chroma
#RUN mkdir /home/app
WORKDIR /home/app

COPY requirements.txt .
RUN pip3 install -r requirements.txt
RUN pip3 install python-dotenv
RUN pip3 install chromadb

COPY . ./

# Asegurar permisos antes de cambiar de usuario
RUN chmod -R 777 /home/app/app/utils/chroma

RUN useradd apprun
USER apprun

CMD ["gunicorn", "app:server", "--preload", "-b 0.0.0.0:8000"]
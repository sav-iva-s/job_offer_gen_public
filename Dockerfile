FROM python:3.13-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY ./requirements.txt .

ENV PATH=/root/.local/bin:$PATH

RUN pip3 install --user -r requirements.txt

FROM python:3.13-slim AS final

ENV USER=appuser
ENV PATH=/home/$USER/.local/bin:$PATH
WORKDIR /app

COPY --from=base --chown=$USER:$USER /root/.local /home/$USER/.local

COPY --chown=$USER:$USER . .

RUN addgroup --gid 10001 $USER \
    && adduser --disabled-password --gecos "" --uid 10001 --ingroup $USER $USER \
    && chown -R $USER:$USER /app

USER $USER 
EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--client.toolbarMode=viewer","--browser.gatherUsageStats=false"]

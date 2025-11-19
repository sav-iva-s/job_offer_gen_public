FROM python:3.13-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --gid 10001 appuser \
    && adduser --disabled-password --gecos "" --uid 10001 --ingroup appuser appuser

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV USER=appuser
ENV PATH=/home/$USER/.local/bin:$PATH

COPY ./requirements.txt .

RUN pip3 install --user -r requirements.txt

FROM python:3.13-slim AS final

ENV USER=appuser
ENV PATH=/home/$USER/.local/bin:$PATH
WORKDIR /app

RUN addgroup --gid 10001 appuser \
    && adduser --disabled-password --gecos "" --uid 10001 --ingroup appuser appuser

COPY --from=base --chown=$USER:$USER /root/.local /home/$USER/.local

COPY --chown=$USER:$USER . .

RUN chown -R $USER:$USER /app

USER $USER
EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--client.toolbarMode=viewer","--browser.gatherUsageStats=false"]

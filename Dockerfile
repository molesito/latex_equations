FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Instalamos LaTeX y latexmk
RUN apt-get update && apt-get install -y --no-install-recommends \
    latexmk \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-latex-extra \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

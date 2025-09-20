FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY . .

RUN uv pip install --system -r requirements.txt

EXPOSE 5555

CMD ["python", "main.py"]
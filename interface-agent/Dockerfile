FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust for tiktoken compilation
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN pip install uv

# Copy requirements first for better caching
COPY requirements.txt /app/requirements.txt
RUN uv pip install --system -r requirements.txt

# Copy the rest of the application
COPY . .

EXPOSE 5555

CMD ["python", "main.py"]
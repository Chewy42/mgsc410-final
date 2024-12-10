FROM python:3.12-slim

WORKDIR /app

# Configure apt to use a different mirror
RUN echo "deb http://archive.debian.org/debian/ bullseye main" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security bullseye/updates main" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make sure the database file exists
RUN python get-db.py

# Run the application
CMD ["python", "app.py"]

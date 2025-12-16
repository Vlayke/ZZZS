# Use a small official Python image.
FROM python:3.11-slim

# All app files will live here in the container.
WORKDIR /app

# Install dependencies first so Docker can cache this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main script into the image.
COPY filter_doctors.py .

# Run the script by default when the container starts.
CMD ["python", "filter_doctors.py"]

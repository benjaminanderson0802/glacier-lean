FROM python:3.12.10-slim-bookworm

WORKDIR /usr/src/app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
CMD ["python", "-m", "src"]

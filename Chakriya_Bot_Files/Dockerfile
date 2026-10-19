FROM python:3.12-slim

WORKDIR /app

RUN useradd -m -u 1000 user

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R 1000:1000 /app

USER user
EXPOSE 7860

CMD ["python", "bot.py"]

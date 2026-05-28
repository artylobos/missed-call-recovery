FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
WORKDIR /app

COPY . /app

EXPOSE 8787

CMD ["python3", "-m", "ai_receptionist_autopilot.server"]

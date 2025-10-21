FROM python:3.13
WORKDIR /app
COPY ./services/full_block /app
COPY requirements.txt /app
COPY shared/config.py /app/shared/config.py
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
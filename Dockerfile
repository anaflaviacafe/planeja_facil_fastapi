FROM python:3.13 

#ENTRYPOINT ["tail", "-f", "/dev/null"]  #keeps the container running, remove to use fastapi

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
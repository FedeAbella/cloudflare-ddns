FROM python:3.13-alpine

WORKDIR /app
COPY ./requirements ./requirements
COPY ./src/*.py ./

RUN pip install --no-cache-dir -r ./requirements

CMD ["python", "-u", "updater.py"]

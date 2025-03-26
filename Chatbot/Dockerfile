FROM rasa/rasa:3.6.21

WORKDIR /app

# Copy files to the container
COPY . .

COPY ./data /app/data

# Install dependencies from requirements.txt
USER root
COPY requirements_docker.txt .
RUN pip install -r requirements_docker.txt

USER root

# CMD ["run","-m","/app/models","--enable-api","--cors","*","--debug" ,"--endpoints", "endpoints.yml", "--debug"]
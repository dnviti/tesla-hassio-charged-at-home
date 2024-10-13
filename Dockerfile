# Step 1: Use an official Python runtime as the base image
FROM python:3.9-slim

# Step 2: Set the working directory in the container
WORKDIR /usr/src/app

# Step 4: Copy the requirements file and the app source code
COPY requirements.txt ./
COPY main.py ./

# Step 9: Start cron in the foreground to keep the container running
CMD ["python", "main.py"]
# Step 1: Use an official Python runtime as a base image
FROM python:3.9-slim

# Step 2: Set the working directory in the container
WORKDIR /usr/src/app

# Step 3: Install necessary dependencies
# Install cron and python dependencies
RUN apt-get update && apt-get install -y cron && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

# Step 4: Copy the requirements file and the app source code
COPY requirements.txt ./
COPY main.py ./

# Step 5: Add the cron job
# Write out a cron job to a file, give execution rights, apply the cron job, and create the log file
RUN echo "59 23 * * * python /usr/src/app/main.py >> /var/log/cron.log 2>&1" > /etc/cron.d/energycron && \
    chmod 0644 /etc/cron.d/energycron && \
    crontab /etc/cron.d/energycron && \
    touch /var/log/cron.log

# Step 7: Run cron in the foreground to keep the container running indefinitely
CMD ["cron", "-f"]
# Step 1: Use an official Python runtime as the base image
FROM python:3.9-slim

# Step 2: Set the working directory in the container
WORKDIR /usr/src/app

# Step 4: Copy the requirements file and the app source code
COPY requirements.txt ./
COPY main.py ./

# Step 3: Install necessary dependencies and configure cron jobs
# Install cron, logrotate, and Python dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    logrotate && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt && \
    # Step 5: Add the cron job
    # Cron job to run main.py every day at 23:59:59 and log output
    echo "59 23 * * * python /usr/src/app/main.py >> /var/log/cron.log 2>&1" > /etc/cron.d/mycron && \
    # Give execution rights to the cron job
    chmod 0644 /etc/cron.d/mycron && crontab /etc/cron.d/mycron && \
    # Step 6: Create the cron log file
    touch /var/log/cron.log && \
    # Step 7: Configure logrotate for log management
    # Create a logrotate config file to rotate cron logs daily
    echo "/var/log/cron.log {\n\
    daily\n\
    missingok\n\
    rotate 7\n\
    compress\n\
    delaycompress\n\
    notifempty\n\
    create 0644 root root\n\
}" > /etc/logrotate.d/cron && \
    # Step 8: Add a cron job to run logrotate daily at midnight
    echo "0 0 * * * /usr/sbin/logrotate /etc/logrotate.conf" >> /etc/cron.d/logrotate

# Step 9: Start cron in the foreground to keep the container running
CMD ["cron", "-f"]
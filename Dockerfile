# Step 1: Use an official Python runtime as a base image
FROM python:3.9-slim

# Step 2: Set the working directory in the container
WORKDIR /usr/src/app

# Step 3: Copy the requirements file and the app source code
COPY requirements.txt ./
COPY . .

# Step 4: Install the required dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 7: Run the application (adjust the command based on your entry point script)
CMD ["python", "main.py"]
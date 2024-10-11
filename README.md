# README

## Overview

This application is a Python-based tool for processing, summarizing, and reporting energy data, particularly focusing on charging energy consumption for a Tesla at home. It interacts with multiple external services such as:

- **MySQL Database**: For storing energy data historically.
- **Home Assistant**: For fetching data related to charging and sending back processed data.
- **Telegram**: For sending periodic summaries about energy consumption.

The application retrieves energy consumption, organizes it into a formatted report, and sends the result to Home Assistant or Telegram if enabled. Moreover, it can store the data in a MySQL (or SQLite) database for historical analysis purposes.

## Features

### 1. MySQL/SQLite Database Support
The application can store data in a database to keep track of energy charged historically. Depending on the configuration, data can be stored either in a **MySQL** database or a **SQLite** database.

- **MySQL**: Ideal for larger datasets and remote database hosting.
- **SQLite**: Local storage within a file, handy for small-scale setups.

### 2. Interaction with Home Assistant
The application talks to **Home Assistant** over its API to both fetch energy data from Home Assistant entities (e.g., Tesla charging sensors) and update states (e.g., “charged at home” sensor). 

### 3. Telegram Notifications
It can send out periodic summaries (e.g., monthly kWh charged at home summaries) via **Telegram** to a specified chat.

## Prerequisites

Before operating the application, ensure the following prerequisites are met:

1. Python 3.9 or higher installed.
2. A working **MySQL** or **SQLite** database instance ready (can be local or remote). For **MySQL**, the credentials (user, host, password) should be available.
3. [**Home Assistant**](https://www.home-assistant.io/) should be up and running, and its API should be accessible with a valid token and URL.
4. [**Telegram Bot**](https://core.telegram.org/bots#6-botfather) is needed to receive notifications if the feature is enabled.

## Configuration

The application’s configuration happens via a file named `config.json`. It contains several sections:

- **Features**: Enable/disable specific features like database, Home Assistant, and Telegram.
- **Database**: Specify the credentials for MySQL or SQLite settings.
- **Telegram**: Specify the token and chat ID for Telegram notifications.
- **Home Assistant**: Specify the API token, base URL, entity filters, and start date.

### Example `config.json`

```json
{
  "features": {
    "use_database": true,
    "send_home_assistant": true,
    "send_telegram": true
  },
  "database": {
    "type": "mysql",
    "host": "localhost",
    "user": "root",
    "password": "yourpassword",
    "dbname": "energy_db"
  },
  "telegram": {
    "token": "your_telegram_token",
    "chat_id": "your_chat_id"
  },
  "home_assistant": {
    "base_url": "https://homeassistant.local:8123",
    "api_token": "your_home_assistant_token",
    "filter_entity_ids": "sensor.tesla_energy",
    "start_date": "2023-01-01"
  }
}
```

## Setup

### Step 1: Install Dependencies

All dependencies are listed in the `requirements.txt` file. To install them, run:

```bash
pip install -r requirements.txt
```

### Step 2: Set Up Configuration

Edit `config.json` to match your settings for the database, Home Assistant, and Telegram. Make sure that valid credentials, such as API tokens and database access, are provided.

### Step 3: Running the Application

Once your configuration is ready, you can run the application by executing:

```bash
python main.py
```

The application will perform the following operations:
- Fetch data from Home Assistant as per the given filters.
- Store the data in MySQL or SQLite if the `use_database` feature is enabled.
- Optionally, send a summary to Telegram if the `send_telegram` feature is enabled.
- Optionally, update Home Assistant sensors with new values if `send_home_assistant` is enabled.

### Step 4: Container Setup (Optional)

To run this application in a Docker container, a `Dockerfile` is provided. You can build and run the Docker container with the following steps:

1. Build the container:

    ```bash
    docker build -t energy-app .
    ```

2. Run the container:

    ```bash
    docker run -v /path_to_config:/usr/src/app/config.json -d energy-app
    ```

   In this command, replace `/path_to_config` with the actual path to your `config.json` file on your machine.

## Features Breakdown

### 1. Database Handling

- **SQLite**: If MySQL is not opted for, the tool defaults to SQLite and will store data in a local file (`local_energy_db.sqlite`).
  
  To enable SQLite storage, set `database.type` to `"sqlite"` in your `config.json`.

- **MySQL**: If you set `database.type` to `"mysql"`, you must provide the necessary credentials (host, user, password, dbname) to connect to the MySQL instance.
  
  Example configuration for MySQL:

  ```json
  "database": {
    "type": "mysql",
    "host": "localhost",
    "user": "root",
    "password": "yourpassword",
    "dbname": "yourdbname"
  }
  ```

### 2. Home Assistant Integration

Data is fetched from Home Assistant using its REST API. An API token and the relevant `base_url` of your Home Assistant instance need to be provided in the config.

Example configuration for Home Assistant:

```json
"home_assistant": {
    "base_url": "https://homeassistant.local:8123",
    "api_token": "your_home_assistant_token",
    "filter_entity_ids": "sensor.energy_consumption",
    "start_date": "2023-01-01"
}
```

### 3. Telegram Integration

If enabled, the application sends a monthly summary message to a provided Telegram chat. You need to configure a Telegram bot and supply the `token` and `chat_id` in the configuration.

Example configuration for Telegram:

```json
"telegram": {
    "token": "your_bot_token",
    "chat_id": "your_chat_id"
}
```

## Conclusion

This energy monitoring application is configurable and capable of running in various environments, whether with **Home Assistant**, **MySQL**, **SQLite**, or **Telegram**. The Docker setup also allows you to containerize the application for easier deployment and scaling.

## Troubleshooting

- **Configuration Loading Failure**: Ensure the `config.json` file is placed in the correct directory and correctly formatted in JSON syntax.
- **Home Assistant Errors**: Check that your API token and base URL are valid. Ensure the correct sensor entities are provided in `filter_entity_ids`.
- **Telegram Errors**: Ensure your token and chat ID are correct. Double-check that the bot has proper permissions.

import requests
import json
import mysql.connector
import sqlite3
from sqlite3 import Error
from collections import defaultdict
from datetime import datetime, timedelta
import os
import telebot

### Utility Functions ###

def extract_date_from_iso(iso_string):
    """ Extract and return the date (YYYY-MM-DD) from an ISO 8601 datetime string. """
    try:
        return datetime.fromisoformat(iso_string.replace('Z', '+00:00')).date()
    except Exception:
        return None

def load_config(config_path='config.json'):
    """ Load the configuration from environment variables, falling back to config.json if not present. """
    
    # Load config file if it exists
    config = {}
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: Could not load config file at '{config_path}'. Continuing with default settings.")

    # Priority to Environment variables, fall back to config if not set
    def get_config_param(param_name, default=None):
        return os.getenv(param_name, config.get(param_name, default))

    features_config = config.get("features", {})
    database_config = config.get("database", {})
    home_assistant_config = config.get("home_assistant", {})
    telegram_config = config.get("telegram", {})

    return {
        "features": {
            "use_database": get_config_param("USE_DATABASE", features_config.get("use_database", False)),
            "send_home_assistant": get_config_param("SEND_HOME_ASSISTANT", features_config.get("send_home_assistant", False)),
            "send_telegram": get_config_param("SEND_TELEGRAM", features_config.get("send_telegram", False)),
        },
        "database": {
            "type": get_config_param("DB_TYPE", database_config.get("type")),
            "db_path": get_config_param("DB_PATH", database_config.get("db_path", "local_energy_db.sqlite")),
            "user": get_config_param("MYSQL_USER", database_config.get("user")),
            "password": get_config_param("MYSQL_PASSWORD", database_config.get("password")),
            "host": get_config_param("MYSQL_HOST", database_config.get("host")),
            "dbname": get_config_param("MYSQL_DB", database_config.get("dbname")),
        },
        "home_assistant": {
            "api_token": get_config_param("HOME_ASSISTANT_TOKEN", home_assistant_config.get("api_token")),
            "base_url": get_config_param("HOME_ASSISTANT_BASE_URL", home_assistant_config.get("base_url")),
            "filter_entity_ids": get_config_param("FILTER_ENTITY_IDS", home_assistant_config.get("filter_entity_ids")),
            "start_date": get_config_param("START_DATE", home_assistant_config.get("start_date")),
        },
        "telegram": {
            "token": get_config_param("TELEGRAM_TOKEN", telegram_config.get("token")),
            "chat_id": get_config_param("TELEGRAM_CHAT_ID", telegram_config.get("chat_id")),
        }
    }

def ensure_sqlite_database_exists(config):
    """ Ensure directory exists before SQLite database is created. """
    db_path = config["database"].get("db_path")
    db_directory = os.path.dirname(db_path)

    if db_directory and not os.path.exists(db_directory):
        os.makedirs(db_directory)

def check_mysql_database_connection(config):
    """ Check if a connection to the MySQL database can be established. """
    try:
        # Attempt to connect to the specified database
        conn = mysql.connector.connect(
            host=config["database"]["host"],
            user=config["database"]["user"],
            password=config["database"]["password"],
            database=config["database"]["dbname"],
            charset='utf8mb4',
            collation='utf8mb4_general_ci'
        )
        print(f"Successfully connected to the MySQL database '{config['database']['dbname']}'")
        return conn
    except mysql.connector.Error as e:
        if e.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:  # Database does not exist
            print(f"The database '{config['database']['dbname']}' does not exist: {e}")
        else:
            print(f"Error connecting to MySQL: {e}")
        return None

def create_db_connection(config):
    """ Establish a database connection based on configuration (MySQL or SQLite). """
    db_type = config.get("database", {}).get("type")
    
    if db_type == "mysql":
        # MySQL connection
        try:
            return check_mysql_database_connection(config)
        except mysql.connector.Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None
    elif db_type == "sqlite":
        # SQLite connection
        db_path = config["database"].get("db_path", "local_energy_db.sqlite")
        try:
            conn = sqlite3.connect(db_path)
            return conn
        except Error as e:
            print(f"Error connecting to SQLite: {e}")
            return None
    else:
        print("Unsupported database type in configuration")
        return None

def create_table_if_needed(conn, db_type='sqlite'):
    """ Create the energy data table if it does not exist. """
    cursor = conn.cursor()
    
    if db_type == 'mysql':
        table_creation_query = '''
        CREATE TABLE IF NOT EXISTS energy_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE NOT NULL,
            charged_kwh FLOAT NOT NULL,
            at_home BOOLEAN NOT NULL
        );
        '''
    else:  # SQLite
        table_creation_query = '''
        CREATE TABLE IF NOT EXISTS energy_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            charged_kwh FLOAT NOT NULL,
            at_home BOOLEAN NOT NULL
        );
        '''
    
    try:
        cursor.execute(table_creation_query)
        conn.commit()
    except Exception as e:
        print(f"Error creating table: {e}")

def insert_daily_summary(conn, data, config):
    """ Insert or update the summaries into the database if the date already exists. """
    db_type = config.get("database", {}).get("type")
        # Use different placeholders depending on the database type
    if db_type == 'mysql':
        placeholder = '%s'
    else:  # SQLite uses '?' as the placeholder
        placeholder = '?'
        
    cursor = conn.cursor()
    
    for entry in data:
        # Check if the date already exists in the database
        check_query = f'''
        SELECT COUNT(*) FROM energy_data WHERE date = {placeholder};
        '''
        cursor.execute(check_query, (entry['date'],))
        count = cursor.fetchone()[0]

        if count > 0:
            # If the date exists, update the entry
            update_query = f'''
            UPDATE energy_data SET charged_kwh = {placeholder} WHERE date = {placeholder};
            '''
            cursor.execute(update_query, (entry['charged_kwh'], entry['date']))
        else:
            # If the date does not exist, insert a new entry
            insert_query = f'''
            INSERT INTO energy_data (date, charged_kwh, at_home) VALUES ({placeholder}, {placeholder}, {placeholder});
            '''
            cursor.execute(insert_query, (entry['date'], entry['charged_kwh'], 1))
    
    conn.commit()

def fetch_previous_month_data(conn, config):
    """ Fetch the total energy charged for the previous month. """
    db_type = config.get("database", {}).get("type")
        # Use different placeholders depending on the database type
    if db_type == 'mysql':
        placeholder = '%s'
    else:  # SQLite uses '?' as the placeholder
        placeholder = '?'
        
    last_day_of_prev_month = (datetime.today().replace(day=1) - timedelta(days=1)).date()
    first_day_of_prev_month = last_day_of_prev_month.replace(day=1)
    
    total_energy_query = f'''
    SELECT SUM(charged_kwh) FROM energy_data WHERE date >= {placeholder} AND date <= {placeholder};
    '''
    cursor = conn.cursor()
    cursor.execute(total_energy_query, (first_day_of_prev_month, last_day_of_prev_month))
    total_energy = cursor.fetchone()[0]
    
    if total_energy is None:
        total_energy = 0.0
        
    return total_energy

def send_telegram_message(config, message):
    """Send a message via Telegram using the BOT API."""
    if not config["features"].get("send_telegram", False):
        return  # Exit if the feature is disabled

    token = config.get("telegram", {}).get("token")
    chat_id = config.get("telegram", {}).get("chat_id")

    if not token or not chat_id:
        print("Telegram token or chat ID is missing in the config.")
        return
    
    bot = telebot.TeleBot(token)
    try:
        bot.send_message(chat_id, message)
        print(f"Message sent to Telegram: {message}")
    except Exception as e:
        print(f"Error sending message via Telegram: {e}")

def send_data_to_homeassistant(config, kwh_value):
    """Send the charged energy data to Home Assistant sensor."""
    if not config["features"].get("send_home_assistant", False):
        return  # Exit if the feature is disabled

    homeassistant_token = config.get("home_assistant", {}).get("api_token")
    
    if not homeassistant_token:
        print("Home Assistant API token is missing from the config file.")
        return
    
    base_url = config.get("home_assistant", {}).get("base_url")
    if not base_url:
        print("Home Assistant base_url is missing from the config file.")
        return
    
    sensor_entity_id = "sensor.corrosivetesla_charged_at_home"
    home_assistant_url = f"{base_url}/api/states/{sensor_entity_id}"
    
    headers = {
        "Authorization": f"Bearer {homeassistant_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "state": kwh_value,
        "attributes": {
            "unit_of_measurement": "kWh",
            "friendly_name": "CorrosiveTesla Charged At Home (kWh)"
        }
    }
    
    try:
        response = requests.post(home_assistant_url, headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"Failed to send data to Home Assistant: {err}")
    else:
        print(f"Data sent to Home Assistant sensor {sensor_entity_id}: {kwh_value} kWh")

### API Data Fetch and Processing ###

def get_summary_of_state(api_url, api_token):
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }

    # Send request to fetch data from API
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching data from API: {e}")
        return None

    # Initialize dictionary to aggregate by date
    daily_energy_data = defaultdict(lambda: {"at_home": False, "charged": 0.0})

    # Process the JSON records
    for record in data:
        date_at_home = None
        sensor_energy_added = None

        for entity in record:
            # Handle device_tracker entry (Check if the device is at home)
            if entity["entity_id"] == "device_tracker.corrosivetesla_location":
                last_reported_date = extract_date_from_iso(entity["last_reported"])
                if entity["state"] == "home" and last_reported_date:
                    date_at_home = last_reported_date  # Set at_home flag for this date

            # Handle sensor.corrosivetesla_charge_energy_added entry (energy added)
            elif entity["entity_id"] == "sensor.corrosivetesla_charge_energy_added":
                last_reported_date = extract_date_from_iso(entity["last_reported"])
                try:
                    energy_value = float(entity["state"])
                except ValueError:
                    continue

                if last_reported_date:
                    sensor_energy_added = (last_reported_date, energy_value)

        # Aggregate the data based on date
        if sensor_energy_added:
            report_date, energy_value = sensor_energy_added
            daily_energy_data[report_date]['charged'] += energy_value

        if date_at_home:
            daily_energy_data[date_at_home]['at_home'] = True

    # Prepare final JSON result where 'at_home' is True and only show the charged energy
    result = [
        {
            "date": day.isoformat(),
            "charged_kwh": values['charged']
        }
        for day, values in sorted(daily_energy_data.items()) if values['at_home']
    ]

    return json.dumps(result, indent=4)

### Main Execution Block ###

config = load_config()

if config:
    # Extract features
    use_database = config["features"].get("use_database", False)
    send_home_assistant = config["features"].get("send_home_assistant", False)
    send_telegram = config["features"].get("send_telegram", False)

    # Get API Parameters
    api_params = config.get("home_assistant", {})
    base_url = api_params.get("base_url")
    API_TOKEN = api_params.get("api_token")
    filter_entity_ids = api_params.get("filter_entity_ids")
    start_date = api_params.get("start_date")

    if base_url and filter_entity_ids and start_date:
        # Construct the API URL using the loaded query parameters
        api_url = f"{base_url}/api/history/period/{start_date}?filter_entity_id={filter_entity_ids}"

        # Get summarized data (unchanged)
        result_json = get_summary_of_state(api_url, API_TOKEN)
        result_data = json.loads(result_json) if result_json else []

        # Handle database interactions if `use_database` is set to True
        if use_database:
            database_type = config["database"].get("type")

            conn = None
            if database_type == "mysql":
                # Connect to MySQL
                conn = create_db_connection(config)
            elif database_type == "sqlite":
                # Handling SQLite database
                ensure_sqlite_database_exists(config)
                conn = create_db_connection(config)
            
            if conn:
                # Create table and store the data
                create_table_if_needed(conn, db_type=database_type)
                insert_daily_summary(conn, result_data, config)
                conn.close()

        # Handle sending summary to Telegram if `send_telegram` is True
        if send_telegram:
            today = datetime.today().date()
            if today.day == 1 and use_database:
                # Fetch last month's summary data from the database
                total_last_month = fetch_previous_month_data(conn, config)
                message = f"Total energy charged last month: {total_last_month:.2f} kWh"

                # Send the summary via Telegram
                send_telegram_message(config, message)

        # Optionally send data to Home Assistant if `send_home_assistant` is True
        if send_home_assistant:
            total_kwh = sum([entry["charged_kwh"] for entry in result_data])
            send_data_to_homeassistant(config, total_kwh)
    else:
        print("Some API query parameters are missing in the config file.")
else:
    print("Configuration loading failed. Please check the config file.")

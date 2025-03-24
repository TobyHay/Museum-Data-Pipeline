"""
Script to run live pipeline - extracts data from kafka producer
Cleans data and loads it into database
"""

import os
import json
import logging
import argparse
from datetime import datetime, time
from dotenv import load_dotenv

import psycopg2
from confluent_kafka import Consumer, Message

load_dotenv()
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", 5432)

KAFKA_TOPIC = 'lmnh'

EXHIBITION_SITE_IDS = ['0', '1', '2', '3', '4', '5']
RATING_VALUES = range(-1, 5)
REQUEST_TYPES = [0, 1]
OPEN_START = time(8, 45)
OPEN_END = time(18, 15)


def setup_kafka() -> Consumer:
    """Sets up kafka config and returns a consumer instance"""

    kafka_config = {
        'bootstrap.servers': os.getenv("BOOTSTRAP_SERVERS"),
        'security.protocol': os.getenv("SECURITY_PROTOCOL"),
        'sasl.mechanisms': os.getenv("SASL_MECHANISM"),
        'sasl.username': os.getenv("USERNAME"),
        'sasl.password': os.getenv("PASSWORD"),
        'group.id': 'c16-toby',
        'auto.offset.reset': 'latest'
    }

    kafka_consumer = Consumer(kafka_config)
    kafka_consumer.subscribe([KAFKA_TOPIC])
    return kafka_consumer


def add_command_line_inputs():
    """Adds command line input, determine logging in the terminal or stored in a file"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-l', '--log', help='Boolean: Logs the process in log.txt file', action='store_true')
    return parser.parse_args()


def set_logger(log_in_file: bool = False) -> logging.Logger:
    """Creates logger"""
    formatter = logging.Formatter(
        "{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
    )
    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    if not log_in_file:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        log.addHandler(stream_handler)

    if log_in_file:
        file_handler = logging.FileHandler(
            "log.txt", mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)
    return log


def convert_to_dict(event: Message) -> dict:
    """Converts the event into a dictionary, if not possible, return None"""
    try:
        values = event.value()
        return json.loads(values)
    except json.JSONDecodeError:
        return None


def format_time(event_date: str) -> str:
    """Formats the time to fit the database"""
    parsed_date = datetime.fromisoformat(event_date)
    return parsed_date.strftime('%Y-%m-%d %H:%M:%S+00')


def validate_info(event_info: dict, log: logging.Logger) -> bool:
    """Runs all functions involved to validate whether the event is storing information correctly"""
    if not event_info:
        return False

    if not validate_time(event_info, log):
        return False

    if not validate_exhibition(event_info, log):
        return False

    if not validate_rating(event_info, log):
        return False

    if not validate_request(event_info, log):
        return False
    return True


def validate_time(event: dict, error_log: logging.Logger) -> bool:
    """Returns True if event time is valid"""
    event_at = event.get("at", None)
    if event_at is None:
        error_log.error("%s - Invalid: Event has no recorded time", event)
        return False

    try:
        parsed_time = datetime.fromisoformat(event_at)
        event_time = parsed_time.time()
    except ValueError:
        error_log.error(
            "%s - Invalid: Event time is not a valid time", event)
        return False

    if not OPEN_START <= event_time <= OPEN_END:
        error_log.error(
            "%s - Invalid: Event recorded outside opening hours", event)
        return False
    return True


def validate_exhibition(event: dict, error_log: logging.Logger) -> bool:
    """Returns True if event exhibition is valid"""
    site = event.get("site", None)

    if site is None:
        error_log.error("%s - Invalid: Event has no site ID", event)
        return False

    if not isinstance(site, str):
        error_log.error(
            "%s - Invalid: Event site is not a valid string", event)
        return False

    if not site.isdigit():
        error_log.error(
            "%s - Invalid: Event site does not have a valid ID", event)
        return False

    if site not in EXHIBITION_SITE_IDS:
        error_log.error(
            "%s - Invalid: Event site ID does not currently exist", event)
        return False
    return True


def validate_rating(event: dict, error_log: logging.Logger) -> bool:
    """Returns True if event rating is valid"""
    value = event.get("val", None)

    if value is None:
        error_log.error("%s - Invalid: Event has no value ID", event)
        return False

    if not isinstance(value, int):
        error_log.error(
            "%s - Invalid: Event value is not a valid integer", event)
        return False

    if value < -1 or value > 4:
        error_log.error(
            "%s - Invalid: Event value is out of bounds", event)
        return False
    return True


def validate_request(event: dict, error_log: logging.Logger) -> bool:
    """Returns True if event request is valid"""
    event_type = event.get("type", None)
    event_value = event.get("val", None)

    if event_type is None and event_value == -1:
        error_log.error("%s - Invalid: Event has no type ID", event)
        return False
    if event_type is None:
        return True

    if event_value != -1:
        error_log.error(
            "%s - Invalid: Event type cannot exist if value is not -1", event)
        return False

    if not isinstance(event_type, int):
        error_log.error(
            "%s - Invalid: Event type is not a valid integer", event)
        return False

    if event_type not in REQUEST_TYPES:
        error_log.error("%s - Invalid: Event type must be -1 or 0", event)
        return False
    return True


def extract_ids(event: dict) -> tuple[int, int, int, str]:
    """Extracts the database IDs from the values given in the event"""
    event_time = event.get("at")
    event_at = format_time(event_time)

    exhibition_id = int(event.get("site"))
    if exhibition_id is not None:
        exhibition_id += 1

    rating_id = event.get("val", None)
    if rating_id is not None:
        rating_id += 1

    request_id = event.get("type", None)
    if request_id is not None:
        request_id += 1

    return rating_id, request_id, exhibition_id, event_at


def upload_to_database(id_info: tuple[int, int, int, str], log) -> None:
    """Uploads the event information to the database"""
    rating_id, request_id, exhibition_id, event_at = id_info

    if request_id is not None:
        event_type = "request"
        type_id = request_id
    else:
        event_type = "rating"
        type_id = rating_id

    conn = psycopg2.connect(
        f"dbname='{DB_NAME}'"
        f"user='{DB_USER}'"
        f"password='{DB_PASSWORD}'"
        f"host='{DB_HOST}'"
        f"port='{DB_PORT}'")

    try:
        cursor = conn.cursor()
        query = f"""INSERT INTO {event_type}_interaction (exhibition_id, {event_type}_id, event_at)
                    VALUES(%s,%s,%s)"""
        cursor.execute(query, (exhibition_id, type_id, event_at))
        conn.commit()
        log.info("Successfully uploaded to database")

    except psycopg2.DatabaseError as de:
        log.error("Unable to upload to database -  %s", de)
    except Exception as e:
        log.error("Unable to upload to database - Unexpected error: %s", e)

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    args = add_command_line_inputs()
    log_file = args.log
    logger = set_logger(log_file)

    consumer = setup_kafka()
    while True:
        message = consumer.poll(1.0)

        if message:
            event_json = convert_to_dict(message)
            if validate_info(event_json, logger):
                logger.info(event_json)

                event_ids = extract_ids(event_json)
                upload_to_database(event_ids, logger)

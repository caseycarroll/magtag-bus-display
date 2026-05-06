import json
import os
import ssl
import time
import wifi
import socketpool
import adafruit_requests
from adafruit_magtag.magtag import MagTag
from adafruit_io.adafruit_io import IO_HTTP

TRIMET_APP_ID = os.getenv("TRIMET_APP_ID")
TRIMET_ARRIVAL_URL = f"https://developer.trimet.org/ws/v2/arrivals?locIDs=423&appID={TRIMET_APP_ID}"

magtag = MagTag(url=TRIMET_ARRIVAL_URL)

class Logger:
    def __init__(self):
        aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
        aio_key = os.getenv("ADAFRUIT_AIO_KEY")
        pool = socketpool.SocketPool(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl.create_default_context())
        try:
            self.io = IO_HTTP(aio_username, aio_key, requests)
            self.log_feed = self.io.get_feed("magtag-logs")
        except Exception as e:
            print(f"Error initializing IO_HTTP: {e}")
            self.io = None
            self.log_feed = None
            magtag.exit_and_deep_sleep(30)
    
    def log(self, message):
        print(message)
        if self.io and self.log_feed:
            try:
                self.io.send_data(self.log_feed["key"], message)
            except Exception as e:
                print(f"Error sending log data: {e}")

logger = Logger()

# Label for Departs
magtag.add_text(
    text_position=(
        12,
        8,
    ),
    line_spacing=1.0,
    text_anchor_point=(0, 0),
    text_scale=1.5,
    is_data=False,
)
magtag.set_text("Departs", 0, auto_refresh=False)

# Label for Next Departure
magtag.add_text(
    text_position=(
        12,
        86,
    ),
    line_spacing=1.0,
    text_anchor_point=(0, 0),
    text_scale=1,
    is_data=False,
)
magtag.set_text("Next Departure", 1, auto_refresh=False)

# Label for Bus Line
magtag.add_text(
    text_position=(
        magtag.graphics.display.width - 12,
        magtag.graphics.display.height - 4,
    ),
    line_spacing=1,
    text_anchor_point=(1, 1),
    text_scale=2,
    is_data=False,
)
magtag.set_text("BUS 15", 2, auto_refresh=False)

# Arrival Time Text
magtag.add_text(
    text_position=(12, 32),
    line_spacing=1.0,
    text_anchor_point=(0, 0),
    text_scale=4,
    is_data=False,
)
magtag.set_text("--:--", 3, auto_refresh=False)

# Next Departure Time
magtag.add_text(
    text_position=(12, magtag.graphics.display.height - 4),
    line_spacing=1.0,
    text_anchor_point=(0, 1),
    text_scale=2,
    is_data=False,
)
magtag.set_text("--:--", 4, auto_refresh=False)

def get_timezone_offset_seconds():
    try: 
        magtag.get_local_time()
        local_now = time.time()
        utc_now = int(magtag.network.get_strftime("%s")) # Request raw UTC seconds from server
        return local_now - utc_now
    except Exception as e:
        logger.log(f"Error getting timezone offset: {e}")
        magtag.exit_and_deep_sleep(30)  # Sleep for 30 seconds before retrying
        return 0

timezone_offset_seconds = get_timezone_offset_seconds()

def format_arrival_time(arrival_ms):
    timestamp_seconds = int(arrival_ms) // 1000
    arrival_time_struct = time.localtime(timestamp_seconds + timezone_offset_seconds)
    hour_24 = arrival_time_struct.tm_hour
    minute = arrival_time_struct.tm_min

    suffix = "am" if hour_24 < 12 else "pm"
    hour_12 = (hour_24 % 12) or 12

    return "{}:{:02d}{}".format(hour_12, minute, suffix)


def fetch_arrival_times():
    try:
        arrivalLogs = []
        response = magtag.fetch(auto_refresh=False)
        data = json.loads(response) if isinstance(response, str) else response
        arrivals = data.get("resultSet", {}).get("arrival", []) if isinstance(data, dict) else []
        # Only render the last two arrivals, oldest to newest.
        last_two_arrivals = arrivals[-2:]
        for display_index, arrival in enumerate(last_two_arrivals):
            print(f"Processing arrival index: {len(arrivals) - len(last_two_arrivals) + display_index}")
            arrival_ms = arrival.get("estimated", arrival.get("scheduled", ""))
            arrival_time = format_arrival_time(arrival_ms)
            magtag.set_text(arrival_time, 3 + display_index, auto_refresh=False)
            arrivalLogs.append(arrival_time)

        logger.log(f"Fetched arrival times: {', '.join(arrivalLogs)}")
        magtag.graphics.display.refresh()
    except Exception as e:
        logger.log(f"Error fetching data: {e}")


while True:
    fetch_arrival_times()
    magtag.enter_light_sleep(300)  # Sleep for 5 minutes (300 seconds)

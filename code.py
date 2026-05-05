import json
import os
import ssl
import time
import wifi
import socketpool
import adafruit_requests
from adafruit_magtag.magtag import MagTag
from adafruit_io.adafruit_io import IO_HTTP

# Initiate logging feed
aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
aio_key = os.getenv("ADAFRUIT_AIO_KEY")
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
io = IO_HTTP(aio_username, aio_key, requests)
log_feed = io.get_feed("magtag-logs")

def log(message):
    print(message)
    io.send_data(log_feed["key"], message)

TRIMET_APP_ID = os.getenv("TRIMET_APP_ID")
TRIMET_ARRIVAL_URL = f"https://developer.trimet.org/ws/v2/arrivals?locIDs=423&appID={TRIMET_APP_ID}"
ARRIVAL1_ESTIMATED = ["resultSet", "arrival", 0, "estimated"]
ARRIVAL2_ESTIMATED = ["resultSet", "arrival", 1, "estimated"]


magtag = MagTag(url=TRIMET_ARRIVAL_URL)

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
magtag.set_text("BUS 14", 2, auto_refresh=False)

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

# Get the current time and calculate the timezone offset
magtag.get_local_time()
local_now = time.time()
utc_now = int(magtag.network.get_strftime("%s")) # Request raw UTC seconds from server
timezone_offset_seconds = local_now - utc_now

def format_arrival_time(arrival_ms):
    timestamp_seconds = int(arrival_ms) // 1000
    arrival_time_struct = time.localtime(timestamp_seconds + timezone_offset_seconds)
    hour_24 = arrival_time_struct.tm_hour
    minute = arrival_time_struct.tm_min

    suffix = "am" if hour_24 < 12 else "pm"
    hour_12 = hour_24 % 12
    if hour_12 == 0:
        hour_12 = 12

    return "{}:{:02d}{}".format(hour_12, minute, suffix)

try:
    response = magtag.fetch(auto_refresh=False)

    # With json_path disabled, fetch may return a raw JSON string.
    data = json.loads(response) if isinstance(response, str) else response
    arrivals = data.get("resultSet", {}).get("arrival", []) if isinstance(data, dict) else []

    arrivalLogs = []
    for i in range(2):
        if i < len(arrivals):
            arrival_time = format_arrival_time(arrivals[i].get("estimated", arrivals[i].get("scheduled", "")))
            magtag.set_text(arrival_time, 3 + i, auto_refresh=False)
            arrivalLogs.append(arrival_time)

    log(f"Fetched arrival times: {', '.join(arrivalLogs)}")
    magtag.graphics.display.refresh()
except (ValueError, RuntimeError) as e:
    log(f"Error fetching data: {e}")

magtag.exit_and_deep_sleep(180)

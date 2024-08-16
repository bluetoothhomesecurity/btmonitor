import os
import datetime
import logging
import json
import pygatt
from time import sleep

with open(os.environ['BTMONITOR_CONFIG']) as f:
   config = json.loads(f.read())


# Custom JSONLineFormatter for JSON Lines format
class JSONLineFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(record.msg)

os.makedirs(config['log_dir'], exist_ok=True)

# Create a logger specifically for Bluetooth devices
device_logger = logging.getLogger('bluetooth_devices')
device_logger.setLevel(logging.INFO)

# Create a file handler for the device log
device_file_handler = logging.FileHandler(f'{config["log_dir"]}/devices.log')
device_file_handler.setLevel(logging.INFO)
device_file_handler.setFormatter(JSONLineFormatter())

# Add the file handler to the device logger
device_logger.addHandler(device_file_handler)

# Create a separate logger for general logging (errors, etc.)
general_logger = logging.getLogger('general')
general_logger.setLevel(logging.INFO)

# Create a console handler for general logging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter for general log messages
general_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(general_formatter)

# Add the console handler to the general logger
general_logger.addHandler(console_handler)

# Define the not detected limit
not_detected_limit = 3

# Delay between each iteration
sleep_time = 5

# Initialize the Bluetooth adapter
adapter = pygatt.GATTToolBackend()
adapter.start()

devices_present = {}
addresses_to_del = []

try:
    while True:
        devices = adapter.scan()
        addresses = set()

        for address in addresses_to_del:
            del devices_present[address]

        addresses_to_del = []

        for device in devices:
            address = device['address']
            addresses.add(address)

            if address not in devices_present:
                # Add new device found
                devices_present[address] = {
                    'address': address,
                    'name': device.get('name', ''),
                    'rssi': device.get('rssi', 'N/A'),
                    'times_not_detected': 0
                }
                log_entry = {
                    'address': address,
                    'name': device.get('name', ''),
                    'rssi': device.get('rssi', 'N/A'),
                    'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'FOUND'
                }
                device_logger.info(log_entry)
                general_logger.info(f'FOUND {address}')

            elif devices_present[address]['times_not_detected'] > 0:
                # Reset times_not_detected if device is detected again
                devices_present[address]['times_not_detected'] = 0

        # Check for lost devices
        for address in list(devices_present):
            if address not in addresses:
                devices_present[address]['times_not_detected'] += 1
                if devices_present[address]['times_not_detected'] == not_detected_limit:
                    log_entry = {
                        'address': address,
                        'name': devices_present[address]['name'],
                        'rssi': devices_present[address]['rssi'],
                        'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'LOST'
                    }
                    device_logger.info(log_entry)
                    addresses_to_del.append(address)
                    general_logger.info(f'LOST {address}')

    sleep(sleep_time)

except Exception as e:
    general_logger.error(f'An error occurred: {e}')
finally:
    adapter.stop()

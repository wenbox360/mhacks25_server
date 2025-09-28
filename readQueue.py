
# Serial read queue for recent values per id
import serial
import threading
import time
from collections import deque

SERIAL_PORT = '/dev/tty.usbmodem101'  # Change as needed
BAUD_RATE = 9600

# Map of id -> deque of recent values
recent_values = {}
MAX_RECENT = 10

def _read_serial():
	try:
		with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1.0) as ser:
			while True:
				line = ser.readline().decode('utf-8').strip()
				if line:
					# Expecting format: "{id},{value};"
					try:
						if line.endswith(';'):
							line = line[:-1]
						id_str, value_str = line.split(',')
						id_int = int(id_str)
						value = value_str
						if id_int not in recent_values:
							recent_values[id_int] = deque(maxlen=MAX_RECENT)
						recent_values[id_int].append(value)
					except Exception as e:
						print(f"Error parsing line '{line}': {e}")
				time.sleep(0.05)
	except Exception as e:
		print(f"Serial read error: {e}")

def start_read_queue():
	"""Start the serial read thread."""
	t = threading.Thread(target=_read_serial, daemon=True)
	t.start()
	print("Serial read queue started")

def get_recent_values(id_int):
	"""Get the 20 most recent values for a given id."""
	return list(recent_values.get(id_int, []))

# sendQueue.py

import serial
import threading
import time
from queue import Queue
from config import DEVICE_TYPE

# Command queue and response storage
send_queue = Queue()
responses = {}
arduino_busy = False

def add_command_to_queue(command):
    """Add a command to the send queue."""
    send_queue.put(command)
    print(f"Added command to queue: {command}")

def get_last_response(key):
    """Get the last response for a given key."""
    return responses.get(key, 0)

def process_queue():
    """Continuously process commands from the queue."""
    
    while True:
        if not send_queue.empty():
            command = send_queue.get()
            
            try:
                if DEVICE_TYPE == "Atmega 32u4":
                    response = _send_cmd_arduino(command)
                elif DEVICE_TYPE == "Raspberry Pi 5":
                    response = _send_cmd_pi(command)
                    
            except Exception as e:
                print(f"Error processing command: {e}")

        time.sleep(0.1)  # Small delay to prevent busy waiting

def _send_cmd_arduino(command):
    """Send a command to the Arduino."""
    try:
        with serial.Serial('/dev/ttyACM0', 9600, timeout=1.0) as ser:
            cmd_str = f"{command['command']},{command['value']};"
            
            ser.write(cmd_str.encode())
            time.sleep(0.1)
            # response = ser.readline().decode('utf-8').strip()
            
            # print(f"Sent: {cmd_str.strip()}, Received: {response}")
            # return response
            
    except Exception as e:
        print(f"Arduino communication error: {e}")
        return "0"

def _send_cmd_pi(command):
    pass

def start_send_queue_processor():
    """Start the queue processing thread."""
    processor_thread = threading.Thread(target=process_queue, daemon=True)
    processor_thread.start()
    print("Queue processor started")
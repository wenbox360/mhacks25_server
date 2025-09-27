# sendQueue.py

import paramiko
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

def wait_for_response(key, timeout=2.0):
    """Wait for a response with timeout."""
    start_time = time.time()
    while key not in responses:
        if time.time() - start_time > timeout:
            print(f"Timeout waiting for response: {key}")
            return 0
        time.sleep(0.05)
    return responses[key]

def process_queue():
    """Continuously process commands from the queue."""
    global arduino_busy
    
    while True:
        if not send_queue.empty() and not arduino_busy:
            command = send_queue.get()
            arduino_busy = True
            
            try:
                if DEVICE_TYPE == "Atmega 32u4":
                    response = _send_cmd_arduino(command)
                elif DEVICE_TYPE == "Raspberry Pi 5":
                    response = _send_cmd_pi(command)
                
                # Store response if it's a read command
                if command.get("type") == "READ":
                    responses[command.get("response_key")] = response
                    
            except Exception as e:
                print(f"Error processing command: {e}")
            finally:
                arduino_busy = False
                
        time.sleep(0.1)  # Small delay to prevent busy waiting

def _send_cmd_arduino(command):
    """Send a command to the Arduino."""
    try:
        with serial.Serial('/dev/ttyACM0', 9600, timeout=1.0) as ser:
            if command["type"] == "READ":
                cmd_str = f"READ:{command['command']}\n"
            else:  # WRITE
                cmd_str = f"WRITE:{command['command']}:{command['value']}\n"
            
            ser.write(cmd_str.encode())
            time.sleep(0.1)
            response = ser.readline().decode('utf-8').strip()
            
            print(f"Sent: {cmd_str.strip()}, Received: {response}")
            return response
            
    except Exception as e:
        print(f"Arduino communication error: {e}")
        return "0"

def _send_cmd_pi(command):
    pass

def start_queue_processor():
    """Start the queue processing thread."""
    processor_thread = threading.Thread(target=process_queue, daemon=True)
    processor_thread.start()
    print("Queue processor started")
# sendQueue.py
import serial
import threading
import time
from queue import Queue, Empty
from config import DEVICE_TYPE

# Command queue and response storage
send_queue = Queue()
responses = {}
_serial = None
_serial_lock = threading.Lock()
SERIAL_PORT = '/dev/cu.usbmodem101'  # <-- set this to the working port you found
BAUD_RATE = 9600
PROCESSOR_STARTED = False

def _open_serial_once():
    global _serial
    with _serial_lock:
        if _serial is not None and _serial.is_open:
            return _serial
        try:
            print(f"[sendQueue] Opening serial port {SERIAL_PORT} @ {BAUD_RATE}")
            _serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            # give Arduino time to reset and boot
            time.sleep(2)
            print("[sendQueue] Serial port opened")
            # optionally read initial lines until READY or timeout
            start = time.time()
            while time.time() - start < 3:
                try:
                    line = _serial.readline().decode("utf-8", errors="ignore").strip()
                except Exception:
                    line = ""
                if line:
                    print(f"[sendQueue] Serial initial line: {line}")
                    if "READY" in line:
                        break
            return _serial
        except Exception as e:
            print(f"[sendQueue] Failed to open serial port: {e}")
            _serial = None
            return None

def add_command_to_queue(command):
    """Add a command to the send queue."""
    send_queue.put(command)
    print(f"[sendQueue] Added command to queue: {command}")

def get_last_response(key):
    """Get the last response for a given key."""
    return responses.get(key)

def _send_via_serial(cmd_str):
    s = _open_serial_once()
    if s is None:
        print("[sendQueue] No serial connection available to send")
        return None
    try:
        # ensure newline terminator for Arduino parsing & flush
        if not cmd_str.endswith("\n"):
            cmd_str = cmd_str + "\n"
        print(f"[sendQueue] Writing to serial: {cmd_str.strip()}")
        s.write(cmd_str.encode())
        s.flush()
        # small delay to let Arduino respond
        time.sleep(0.05)
        try:
            resp = s.readline().decode("utf-8", errors="ignore").strip()
        except Exception:
            resp = ""
        if resp:
            print(f"[sendQueue] Read from serial: {resp}")
            return resp
        return "OK"
    except Exception as e:
        print(f"[sendQueue] Error writing to serial: {e}")
        return None

def _process_loop():
    global PROCESSOR_STARTED
    PROCESSOR_STARTED = True
    print("[sendQueue] process_queue started")
    _open_serial_once()
    while True:
        try:
            command = send_queue.get(timeout=0.5)
        except Empty:
            time.sleep(0.01)
            continue

        try:
            # Expecting command to be dict {command: int, value: ..., response_key: optional}
            cmd_num = command.get("command")
            cmd_val = command.get("value", "")
            cmd_str = f"{cmd_num},{cmd_val};"
            resp = _send_via_serial(cmd_str)

            key = command.get("response_key")
            if key:
                responses[key] = resp

            print(f"[sendQueue] Processed command -> response: {resp}")
        except Exception as e:
            print(f"[sendQueue] Error processing command: {e}")
        finally:
            send_queue.task_done()
        time.sleep(0.01)

def start_send_queue_processor():
    """Start the queue processing thread (idempotent)."""
    global PROCESSOR_STARTED
    if PROCESSOR_STARTED:
        print("[sendQueue] Processor already started")
        return
    processor_thread = threading.Thread(target=_process_loop, daemon=True)
    processor_thread.start()
    print("[sendQueue] Queue processor thread started")

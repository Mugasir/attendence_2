#!/usr/bin/env python3
"""
NFC Reader Daemon
Continuously listens for NFC card taps and sends to API.

Supports:
  - ACR122U (via nfcpy / libusb)
  - PN532 via UART/SPI/I2C (via pn532)
  - Simulation mode (for testing without hardware)

Usage:
  python3 nfc_reader.py --reader acr122u --api http://localhost:5000
  python3 nfc_reader.py --reader pn532 --port /dev/ttyAMA0
  python3 nfc_reader.py --simulate   # test mode
"""

import argparse
import time
import requests
import json
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('nfc_reader.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('nfc_reader')


class NFCReaderBase:
    def read_uid(self):
        raise NotImplementedError


class ACR122UReader(NFCReaderBase):
    """ACR122U via nfcpy library."""
    def __init__(self):
        try:
            import nfc
            self.clf = nfc.ContactlessFrontend('usb')
            log.info("✅ ACR122U connected via nfcpy")
        except Exception as e:
            log.error(f"ACR122U init failed: {e}")
            raise

    def read_uid(self, timeout=5):
        import nfc
        tag = self.clf.connect(rdwr={'on-connect': lambda tag: False})
        if tag:
            return tag.identifier.hex().upper()
        return None


class PN532Reader(NFCReaderBase):
    """PN532 via UART (Raspberry Pi GPIO)."""
    def __init__(self, port='/dev/ttyAMA0', baudrate=115200):
        try:
            from pn532 import PN532_UART
            self.pn532 = PN532_UART(port, baudrate=baudrate, debug=False)
            self.pn532.begin()
            self.pn532.SAM_configuration()
            log.info(f"✅ PN532 connected on {port}")
        except Exception as e:
            log.error(f"PN532 init failed: {e}")
            raise

    def read_uid(self, timeout=5):
        uid = self.pn532.read_passive_target(timeout=timeout)
        if uid:
            return ''.join([format(b, '02X') for b in uid])
        return None


class SimulatedReader(NFCReaderBase):
    """Simulated reader for testing — reads UIDs from keyboard."""
    def read_uid(self, timeout=None):
        try:
            uid = input("\n[SIM] Enter card UID (or press Enter to skip): ").strip().upper()
            return uid if uid else None
        except (KeyboardInterrupt, EOFError):
            return None


def send_scan(api_url, card_uid, entry_point='main'):
    """Send card UID to the Flask API."""
    try:
        resp = requests.post(
            f'{api_url}/api/attendance/scan',
            json={'card_uid': card_uid, 'entry_point': entry_point},
            timeout=5
        )
        data = resp.json()
        status = data.get('status', 'unknown')
        message = data.get('message', '')
        student = data.get('student', {})

        log.info(f"[{status.upper()}] {student.get('full_name', 'Unknown')} - {message}")

        # Display to terminal (for Raspberry Pi kiosk display)
        print("\n" + "="*50)
        if status == 'clock_in':
            print(f"  ✅ CLOCK IN")
            print(f"  👤 {student.get('full_name')}")
            print(f"  🎓 {student.get('course')} Year {student.get('year')}")
            print(f"  🕐 Time In: {data.get('time_in')}")
            print(f"  {message}")
        elif status == 'clock_out':
            print(f"  🚪 CLOCK OUT")
            print(f"  👤 {student.get('full_name')}")
            print(f"  ⏱️  Duration: {data.get('duration_minutes')} minutes")
            print(f"  {message}")
        else:
            print(f"  ❌ ERROR: {message}")
        print("="*50 + "\n")

        return data

    except requests.exceptions.ConnectionError:
        log.error("❌ Cannot connect to API server. Is Flask running?")
    except Exception as e:
        log.error(f"❌ Scan error: {e}")
    return None


def main():
    parser = argparse.ArgumentParser(description='NFC Attendance Reader Daemon')
    parser.add_argument('--reader', choices=['acr122u', 'pn532'], help='NFC reader type')
    parser.add_argument('--port', default='/dev/ttyAMA0', help='Serial port for PN532')
    parser.add_argument('--api', default='http://localhost:5000', help='API base URL')
    parser.add_argument('--entry', default='main', help='Entry point name')
    parser.add_argument('--simulate', action='store_true', help='Use simulated reader')
    args = parser.parse_args()

    log.info("🚀 NFC Attendance Reader starting...")
    log.info(f"📡 API: {args.api}")
    log.info(f"🚪 Entry point: {args.entry}")

    # Init reader
    if args.simulate:
        reader = SimulatedReader()
        log.info("⚠️  Running in SIMULATION mode")
    elif args.reader == 'acr122u':
        reader = ACR122UReader()
    elif args.reader == 'pn532':
        reader = PN532Reader(port=args.port)
    else:
        log.error("No reader specified. Use --reader acr122u|pn532 or --simulate")
        return

    log.info("👂 Listening for NFC cards... (Ctrl+C to stop)\n")

    last_uid = None
    last_scan_time = 0
    DEBOUNCE_SECONDS = 3  # Prevent duplicate scans

    while True:
        try:
            uid = reader.read_uid()
            now = time.time()

            if uid:
                # Debounce: ignore same card scanned within 3 seconds
                if uid == last_uid and (now - last_scan_time) < DEBOUNCE_SECONDS:
                    time.sleep(0.5)
                    continue

                last_uid = uid
                last_scan_time = now

                log.info(f"📶 Card detected: {uid}")
                send_scan(args.api, uid, args.entry)
                time.sleep(1)  # Brief pause after successful scan
            else:
                time.sleep(0.1)  # Polling interval

        except KeyboardInterrupt:
            log.info("\n👋 NFC Reader stopped.")
            break
        except Exception as e:
            log.error(f"Reader error: {e}")
            time.sleep(2)


if __name__ == '__main__':
    main()

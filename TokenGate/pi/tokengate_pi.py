#!/usr/bin/env python3
# TokenGate Pi listener — queued handling & start-after-launch
# LEDs: BCM 18 (red), 27 (green) | Servo: BCM 19 | OLED: SSD1306 @ 0x3C on I2C bus 1
# Env: RPCURL, GATE_ADDRESS
import os, sys, time, signal, threading
from queue import Queue, Empty
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import Web3RPCError
import gpiod
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

# ---------- GPIO/servo config ----------
GPIO_CHIP = "/dev/gpiochip4"   # change if your system uses a different one
LED_RED_PIN = 18
LED_GREEN_PIN = 27
SERVO_PIN = 19

FREQ_HZ  = 50.0
PERIOD_S = 1.0 / FREQ_HZ
MIN_US, CENTER_US, MAX_US = 600, 1500, 2400
POLL_INTERVAL = 1.0  # seconds

# ---------- Minimal ABI: GatePulse ----------
EVENT_SIG = "GatePulse(uint256,address,uint256,uint256)"
GATE_ABI = [{
    "type": "event",
    "name": "GatePulse",
    "anonymous": False,  # <-- important for web3 event decoder
    "inputs": [
        {"indexed": False, "name": "value",     "type": "uint256"},
        {"indexed": True,  "name": "from",      "type": "address"},
        {"indexed": False, "name": "amount",    "type": "uint256"},
        {"indexed": False, "name": "timestamp", "type": "uint256"}
    ]
}]

# ---------- OLED ----------
class OLED:
    def __init__(self):
        self.serial = i2c(port=1, address=0x3C)
        self.dev = ssd1306(self.serial)
        # Bigger font (falls back to default if not found)
        try:
            self.font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12  # <-- change size here
            )
        except Exception:
            self.font = ImageFont.load_default()
        # Precompute line height (Pillow 10+: use getbbox)
        box = self.font.getbbox("A")
        self.line_h = (box[3] - box[1]) + 2
        self.clear()

    def clear(self):
        img = Image.new("1", self.dev.size, 0)
        self.dev.display(img)

    def text(self, lines):
        W, H = self.dev.size
        img = Image.new("1", (W, H), 0)
        d = ImageDraw.Draw(img)
        y = 0
        for ln in lines:
            d.text((0, y), ln, 255, font=self.font)
            y += self.line_h
        self.dev.display(img)


# ---------- GPIO (libgpiod v1-style) ----------
def open_line(chip, offset):
    line = chip.get_line(offset)
    line.request(consumer="tokengate", type=gpiod.LINE_REQ_DIR_OUT, default_val=0)
    return line

def drive_servo_us(line, high_us, duration_s):
    """Software PWM @50Hz for duration_s seconds."""
    high_s = max(0.0, min(PERIOD_S, high_us / 1_000_000.0))
    cycles = max(1, int(duration_s / PERIOD_S))
    for _ in range(cycles):
        line.set_value(1); time.sleep(high_s)
        line.set_value(0); low_s = PERIOD_S - high_s
        if low_s > 0: time.sleep(low_s)

def center(line, seconds=0.5): drive_servo_us(line, CENTER_US, seconds)
def maxpos(line, seconds=1.0): drive_servo_us(line, MAX_US, seconds)

# ---------- Worker: consume events sequentially ----------
def worker_loop(stop_flag, q, oled, servo, led_r, led_g):
    while not stop_flag.is_set():
        try:
            evt = q.get(timeout=0.2)  # (value, sender, blk, txhash, logIndex)
        except Empty:
            continue
        value, sender, blk, txh, lidx = evt
        print(f"[Worker] handling value={value} from={sender} blk={blk} tx={txh} idx={lidx} (queue={q.qsize()})")
        try:
            if value <= 0:
                oled.text(["TokenGate", "Pulse: 0s", f"CENTER | Q:{q.qsize()}"])
                led_r.set_value(1); led_g.set_value(0)
                center(servo, 0.5)
            else:
                # MAX with countdown (one-second steps)
                led_r.set_value(0); led_g.set_value(1)
                for remaining in range(value, 0, -1):
                    oled.text([f"Pulse: {value}s", f"Remaining: {remaining}s", f"Q:{q.qsize()}"])
                    maxpos(servo, 1.0)
                # Return to center
                center(servo, 0.6)
                led_r.set_value(1); led_g.set_value(0)
                oled.text(["TokenGate", "CENTER", f"Q:{q.qsize()}"])
        except Exception as e:
            print(f"[Worker] error: {e}", file=sys.stderr)
        finally:
            q.task_done()

# ---------- Main ----------
def main():
    load_dotenv()  # loads .env in cwd if present
    RPCURL = os.getenv("RPCURL")
    GATE_ADDRESS = os.getenv("GATE_ADDRESS")
    if not RPCURL or not GATE_ADDRESS:
        print("ERROR: Set RPCURL and GATE_ADDRESS (in env or .env).", file=sys.stderr)
        sys.exit(2)

    w3 = Web3(Web3.HTTPProvider(RPCURL, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        print("ERROR: Web3 not connected to RPCURL.", file=sys.stderr); sys.exit(2)

    gate_addr = Web3.to_checksum_address(GATE_ADDRESS)
    gate = w3.eth.contract(address=gate_addr, abi=GATE_ABI)

    topic0_hexbytes = w3.keccak(text=EVENT_SIG)
    topic0_str = topic0_hexbytes.hex()
    print(f"[EventSig] {EVENT_SIG} -> {topic0_str}")

    # Setup hardware
    oled = OLED(); oled.text(["TokenGate", "Starting…"])
    chip = gpiod.Chip(GPIO_CHIP)
    led_r = open_line(chip, LED_RED_PIN)
    led_g = open_line(chip, LED_GREEN_PIN)
    servo = open_line(chip, SERVO_PIN)

    # Idle state at launch
    center(servo, 0.6)
    led_r.set_value(1); led_g.set_value(0)
    oled.text(["TokenGate", "Waiting for events…", "Q:0"])

    # Queued processing
    q = Queue(maxsize=256)
    stop_flag = threading.Event()
    t_worker = threading.Thread(target=worker_loop, args=(stop_flag, q, oled, servo, led_r, led_g), daemon=True)
    t_worker.start()

    # IMPORTANT: start AFTER launch — ignore any history
    last_block = w3.eth.block_number

    # de-dup set: "txhash:logIndex"
    seen = set()

    # graceful signals
    def _sig(*_): stop_flag.set()
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    try:
        while not stop_flag.is_set():
            tip = w3.eth.block_number
            if tip > last_block:
                params = {
                    "fromBlock": last_block + 1,  # strictly after launch
                    "toBlock": tip,
                    "address": gate_addr,
                    "topics": [topic0_hexbytes],  # HexBytes safest
                }
                try:
                    logs = w3.eth.get_logs(params)
                except Web3RPCError:
                    # Some RPCs insist on string "0x..." topics
                    t0 = topic0_str if topic0_str.startswith("0x") else ("0x" + topic0_str)
                    params["topics"] = [t0]
                    logs = w3.eth.get_logs(params)

                # Ensure deterministic ordering: by (blockNumber, logIndex)
                logs.sort(key=lambda lg: (lg["blockNumber"], lg["logIndex"]))

                for lg in logs:
                    # Guard against any odd/partial log
                    try:
                        ev = gate.events.GatePulse().process_log(lg)
                    except Exception as e:
                        print(f"[Decode] skip log: {e}", file=sys.stderr)
                        continue

                    value  = int(ev["args"]["value"])
                    sender = ev["args"]["from"]
                    blk    = lg["blockNumber"]
                    txh    = lg["transactionHash"].hex()
                    lidx   = lg["logIndex"]

                    uid = f"{txh}:{lidx}"
                    if uid in seen:
                        continue
                    seen.add(uid)

                    # ENQUEUE — worker thread will run them sequentially
                    try:
                        q.put_nowait((value, sender, blk, txh, lidx))
                        print(f"[Enqueue] value={value} from={sender} blk={blk} idx={lidx} (queue={q.qsize()})")
                    except:
                        print("[Enqueue] queue full — dropping event", file=sys.stderr)

                last_block = tip
                # occasionally trim the seen set
                if len(seen) > 2048:
                    seen = set(list(seen)[-1024:])
            time.sleep(POLL_INTERVAL)

        # drain queue before exit
        q.join()
    finally:
        try:
            center(servo, 0.4); led_r.set_value(0); led_g.set_value(0)
        except Exception:
            pass
        try:
            servo.set_value(0); servo.release()
            led_r.set_value(0); led_r.release()
            led_g.set_value(0); led_g.release()
            chip.close()
        except Exception:
            pass
        try:
            oled.text(["TokenGate", "Stopped"])
        except Exception:
            pass

if __name__ == "__main__":
    main()

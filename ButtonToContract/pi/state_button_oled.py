#!/usr/bin/env python3
"""
Button + OLED + RGB LED (gpiod v1) + Web3 contract toggle, with robust state sync
OFF => red, ON => green. LED keeps final color after each toggle.

Wiring (BCM):
  Button -> GPIO17 (pin 11) to GND (active-LOW)
  LED R  -> 220–330Ω -> GPIO18 (pin 12)
  LED G  -> 220–330Ω -> GPIO27 (pin 13)
  LED common -> GND
  OLED SSD1306 128x64 @ 0x3C: SDA->GPIO2, SCL->GPIO3, VCC->3V3, GND->GND

.env:
  RPC_URL=https://sepolia.base.org
  CHAIN_ID=84532
  CONTRACT_ADDRESS=0xYourContract
  PRIVATE_KEY=0xyourprivatekeyhex
  MAX_FEE_GWEI=1.5
  MAX_PRIORITY_FEE_GWEI=0.2
  # GPIO_CHIP=/dev/gpiochip4 (optional)
"""

import os, sys, time, threading, signal
import gpiod
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError

from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306

# ---------- Config ----------
BUTTON = 17
LED_R  = 18
LED_G  = 27
COMMON_CATHODE = True

GPIO_CHIP = os.getenv("GPIO_CHIP", "/dev/gpiochip4")
I2C_BUS   = 1
OLED_ADDR = 0x3C

DEBOUNCE_S = 0.06

STATE_READ_RETRIES   = 5
STATE_READ_DELAY_S   = 0.4
STATE_POLL_S         = 0.5
STATE_WAIT_TIMEOUT_S = 20.0

ABI = [
    {"inputs":[],"name":"changeState","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"readState","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
]

stop_ev    = threading.Event()
flicker_ev = threading.Event()

# ---------- OLED ----------
def oled_make():
    serial = i2c(port=I2C_BUS, address=OLED_ADDR)
    dev = ssd1306(serial, width=128, height=64)
    dev.clear()
    return dev

def oled_center(dev, text, note=None):
    img = Image.new("1", (dev.width, dev.height))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    w, h = d.textbbox((0,0), text, font=font)[2:]
    d.text(((dev.width - w)//2, (dev.height - h)//2), text, 255, font=font)
    if note:
        w2, h2 = d.textbbox((0,0), note, font=font)[2:]
        d.text(((dev.width - w2)//2, dev.height - h2 - 2), note, 255, font=font)
    dev.display(img)

# ---------- GPIO (libgpiod v1) ----------
class GPIO:
    def __init__(self, chip_path):
        self.chip = gpiod.Chip(chip_path)
        self.line_r = self.chip.get_line(LED_R)
        self.line_g = self.chip.get_line(LED_G)
        self.line_r.request(consumer="onchain-toggle", type=gpiod.LINE_REQ_DIR_OUT, default_val=0)
        self.line_g.request(consumer="onchain-toggle", type=gpiod.LINE_REQ_DIR_OUT, default_val=0)
        self.btn = self.chip.get_line(BUTTON)
        flags = 0
        if hasattr(gpiod, "LINE_REQ_FLAG_BIAS_PULL_UP"):
            flags |= gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
        self.btn.request(consumer="onchain-toggle", type=gpiod.LINE_REQ_DIR_IN, flags=flags)

    def _level(self, on: bool) -> int:
        return 1 if (COMMON_CATHODE and on) or ((not COMMON_CATHODE) and (not on)) else 0

    def set_red(self, on: bool):   self.line_r.set_value(self._level(on))
    def set_green(self, on: bool): self.line_g.set_value(self._level(on))

    def set_color(self, color: str):
        if color == "red":
            self.set_red(True); self.set_green(False)
        elif color == "green":
            self.set_red(False); self.set_green(True)
        else:
            self.set_red(False); self.set_green(False)

    def button_pressed(self) -> bool:
        return self.btn.get_value() == 0  # active-LOW

    def wait_press(self) -> bool:
        while not stop_ev.is_set():
            if self.button_pressed():
                t0 = time.monotonic()
                ok = True
                while time.monotonic() - t0 < DEBOUNCE_S:
                    if stop_ev.is_set(): return False
                    if not self.button_pressed():
                        ok = False; break
                    time.sleep(0.005)
                if ok:
                    while not stop_ev.is_set() and self.button_pressed():
                        time.sleep(0.005)
                    return True
            time.sleep(0.005)
        return False

    def off(self): self.set_color("off")

    def close(self):
        try:
            self.off()
            self.line_r.release(); self.line_g.release(); self.btn.release()
            self.chip.close()
        except Exception:
            pass

def flicker(gpio: GPIO, period=0.08):
    # NOTE: do NOT change LEDs when exiting — main thread will set final color.
    while flicker_ev.is_set() and not stop_ev.is_set():
        gpio.set_color("red");   time.sleep(period)
        gpio.set_color("green"); time.sleep(period)

# ---------- Web3 ----------
def load_chain():
    load_dotenv()
    rpc  = os.getenv("RPC_URL")
    cid  = int(os.getenv("CHAIN_ID", "0"))
    addr = os.getenv("CONTRACT_ADDRESS")
    pk   = os.getenv("PRIVATE_KEY")
    max_fee = float(os.getenv("MAX_FEE_GWEI", "1.5"))
    max_tip = float(os.getenv("MAX_PRIORITY_FEE_GWEI", "0.2"))

    if not (rpc and cid and addr and pk):
        print("Missing RPC_URL / CHAIN_ID / CONTRACT_ADDRESS / PRIVATE_KEY in .env", file=sys.stderr)
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        print("Cannot connect to RPC", file=sys.stderr); sys.exit(1)

    acct = w3.eth.account.from_key(pk)
    con  = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=ABI)
    caps = {
        "maxFeePerGas":         w3.to_wei(max_fee, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(max_tip, "gwei"),
    }
    return w3, acct, con, cid, caps

def read_state(contract, block_identifier="latest") -> str:
    return contract.functions.readState().call(block_identifier=block_identifier).upper()

def read_state_retry(contract, block_identifier="latest", tries=STATE_READ_RETRIES, delay=STATE_READ_DELAY_S) -> str:
    last = None
    for _ in range(tries):
        try: return read_state(contract, block_identifier)
        except Exception as e:
            last = e; time.sleep(delay)
    raise last

def send_toggle(w3, acct, contract, chain_id, caps) -> str:
    nonce = w3.eth.get_transaction_count(acct.address, "pending")
    tx = contract.functions.changeState().build_transaction({
        "from": acct.address,
        "chainId": chain_id,
        "nonce": nonce,
        "type": 2,
        "gas": 120000,
        **caps,
    })
    signed = acct.sign_transaction(tx)
    raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
    if raw is None:
        raise AttributeError("SignedTransaction missing rawTransaction/raw_transaction")
    return w3.eth.send_raw_transaction(raw).hex()

def wait_until_state_latest(contract, target: str, timeout_s=STATE_WAIT_TIMEOUT_S, poll_s=STATE_POLL_S) -> bool:
    end = time.monotonic() + timeout_s
    while time.monotonic() < end and not stop_ev.is_set():
        try:
            if read_state(contract, "latest") == target:
                return True
        except Exception:
            pass
        time.sleep(poll_s)
    return False

def set_ui_from_state(gpio: GPIO, oled, state_str: str):
    gpio.set_color("green" if state_str == "ON" else "red")
    oled_center(oled, state_str, "Press to toggle")
    print(f"[STATE] {state_str}", flush=True)

# ---------- Main ----------
def main():
    signal.signal(signal.SIGINT,  lambda *_: stop_ev.set())
    signal.signal(signal.SIGTERM, lambda *_: stop_ev.set())

    gpio = GPIO(GPIO_CHIP)
    oled = oled_make()
    w3, acct, contract, chain_id, caps = load_chain()

    oled_center(oled, "Starting", "connecting…")
    try:
        s0 = read_state_retry(contract, "latest")
        set_ui_from_state(gpio, oled, s0)
    except Exception as e:
        oled_center(oled, "Error", "read failed"); gpio.off()
        print(f"[ERROR] initial readState: {e}", file=sys.stderr)

    print("Ready. Press button to toggle. Ctrl+C to exit.")
    while not stop_ev.is_set():
        if not gpio.wait_press():
            break

        # Start flicker first
        oled_center(oled, "Toggle")
        flicker_ev.set()
        t = threading.Thread(target=flicker, args=(gpio,), daemon=True); t.start()

        final_state = None
        try:
            before = read_state_retry(contract, "latest")
            target = "OFF" if before == "ON" else "ON"

            txh = send_toggle(w3, acct, contract, chain_id, caps)
            oled_center(oled, "Pending…", txh[:8] + "…")
            rcpt = w3.eth.wait_for_transaction_receipt(txh, timeout=180)

            # Verify at inclusion block, then ensure latest catches up
            try:
                s_block = read_state_retry(contract, block_identifier=rcpt.blockNumber)
            except Exception as e:
                s_block = None
                print(f"[WARN] read at block failed: {e}", file=sys.stderr)

            if s_block != target:
                oled_center(oled, "Syncing…", "waiting state")
                ok = wait_until_state_latest(contract, target)
                if not ok:
                    print(f"[WARN] target '{target}' not seen on latest within timeout", file=sys.stderr)

            # Decide final state from latest (or target as fallback)
            try:
                final_state = read_state_retry(contract, "latest")
            except Exception as e:
                final_state = target
                print(f"[WARN] final read failed, using target: {e}", file=sys.stderr)

        except ContractLogicError:
            final_state = None
            oled_center(oled, "Denied", "not owner?")
        except Exception as e:
            final_state = None
            oled_center(oled, "Error", "toggle failed")
            print(f"[ERROR] toggle: {e}", file=sys.stderr)
        finally:
            # STOP FLICKER FIRST, then set final LED color to avoid races
            flicker_ev.clear()
            try: t.join(timeout=1.0)
            except: pass

            if final_state in ("ON", "OFF"):
                set_ui_from_state(gpio, oled, final_state)
            elif final_state is None:
                # leave OLED as-is; ensure LED not stuck off
                try:
                    s_latest = read_state_retry(contract, "latest")
                    set_ui_from_state(gpio, oled, s_latest)
                except Exception:
                    gpio.off()

    gpio.off()
    oled_center(oled, "Bye")
    gpio.close()
    print("\nClean exit.")

if __name__ == "__main__":
    main()

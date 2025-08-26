#!/usr/bin/env python3
# libgpiod v1 smoketest: Red->GPIO18, Green->GPIO27, common cathode (active-high)

import os, sys, time
import gpiod

CHIP  = os.getenv("GPIO_CHIP", "/dev/gpiochip4")
RED   = 18
GREEN = 27

print(f"[INFO] Using chip: {CHIP}")
try:
    chip  = gpiod.Chip(CHIP)
    lines = chip.get_lines([RED, GREEN])
    # Request both as outputs, start low
    lines.request(consumer="led-smoketest", type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0, 0])
    print("[OK] Requested lines 18 (RED) and 27 (GREEN)")
except PermissionError:
    print("ERROR: Permission denied. Add your user to 'gpio' group or run with sudo.", file=sys.stderr)
    sys.exit(2)
except Exception as e:
    print(f"ERROR: GPIO request failed: {e}", file=sys.stderr)
    sys.exit(3)

def set_leds(r_on, g_on):
    # common cathode -> active-high (1=on)
    lines.set_values([1 if r_on else 0, 1 if g_on else 0])

try:
    print("[TEST] RED on");   set_leds(True, False);  time.sleep(0.6)
    print("[TEST] RED off");  set_leds(False, False); time.sleep(0.3)
    print("[TEST] GREEN on"); set_leds(False, True);  time.sleep(0.6)
    print("[TEST] GREEN off");set_leds(False, False); time.sleep(0.3)
    print("[TEST] BOTH on (yellow)"); set_leds(True, True); time.sleep(0.6)
    set_leds(False, False)
    print("[PASS] LED smoketest completed.")
except KeyboardInterrupt:
    pass
finally:
    try:
        set_leds(False, False)
        lines.release()
        chip.close()
    except Exception:
        pass

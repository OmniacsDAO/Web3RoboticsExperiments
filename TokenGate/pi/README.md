# TokenGate / pi (Raspberry Pi listener)

Listens for `GatePulse` events from `TokenGate` and animates:
- **OLED** (SSD1306 128×64 @ I²C `0x3C`): status, queue, countdown
- **LEDs** (BCM 18 red, 27 green)
- **Servo** (BCM 19): runs `value` seconds per pulse

## Hardware & Wiring

- OLED SSD1306 (I²C): SDA → GPIO2, SCL → GPIO3, 3V3, GND
- LEDs: BCM18 (red), BCM27 (green) through resistors to 3V3/GND as appropriate
- Servo on BCM19 (ensure separate 5V power rail if needed; common ground)

## Pi Setup

Enable I²C and install system deps:
```bash
sudo apt update
sudo apt install -y raspi-config i2c-tools gpiod python3-libgpiod python3-pip python3-venv
sudo raspi-config  # Interface Options → I2C → Enable
i2cdetect -y 1     # OLED typically shows at 0x3C
sudo adduser $USER gpio
sudo adduser $USER i2c
newgrp gpio && newgrp i2c
````

Create venv & install Python deps:

```bash
python3 -m venv .venv --system-site-packages && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` includes: `Pillow`, `smbus2`, `luma.oled`, `python-dotenv`, `web3`.&#x20;

## Configure

```bash
cp .env.example .env
# .env
RPCURL="https://sepolia.base.org"
GATE_ADDRESS="0xYourGateAddress"
```

## Run

```bash
source .venv/bin/activate
python3 tokengate_pi.py
```

* The app fetches `GatePulse` logs from `GATE_ADDRESS`.
* For each pulse:

  * `value <= 0`: red LED, servo centers.
  * `value > 0`: green LED; servo runs for `value` seconds with OLED countdown.

## Make the OLED font bigger

Open `tokengate_pi.py` and adjust the `ImageFont.truetype(..., <size>)` (default 12). Search for the line with `DejaVuSans.ttf` and increase the size (e.g., 14–18) to taste.

## Troubleshooting

* **OLED not detected**: confirm `i2cdetect -y 1` shows `0x3C`; check cabling.
* **Permissions**: ensure your user is in `gpio` and `i2c` groups; re-login or `newgrp`.
* **Logs decode error**: the app auto-retries topic formatting (`0x...`) for some RPCs.
* **Servo jitter**: provide adequate 5V power; share ground between Pi and servo supply.

---

🧠 Built with purpose by Omniacs.DAO • Back us with $IACS → 0x46e69Fa9059C3D5F8933CA5E993158568DC80EBf (Base)
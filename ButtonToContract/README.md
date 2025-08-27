# Raspberry Pi 5 ↔ Base Sepolia ON/OFF Toggle (OLED + RGB LED)

A Raspberry Pi 5 button toggles an on-chain **Switch** contract. The OLED shows `ON/OFF`, and an RGB LED mirrors the state (GREEN = ON, RED = OFF). While reading the contract or waiting for a transaction to confirm, the OLED shows progress and the LED flickers.

## Folder name
`web3RoboticsExperiments/ButtonToContract`

## Repo structure
```
ButtonToContract/
├─ chain/                       # Hardhat project (Node/Hardhat files)
│  ├─ contracts/
│  │  └─ Switch.sol
│  ├─ scripts/
│  │  └─ deploy.js
│  ├─ hardhat.config.js
│  ├─ package.json
│  ├─ .env.example
│  └─ README.md
├─ pi/
│  ├─ state_button_oled.py
│  └─ .env.example
├─ requirements.txt
└─ README.md
```

## Hardware (BCM pinout)

| Part        | BCM Pin | Header | Notes                                  |
|-------------|---------|--------|----------------------------------------|
| Button      | GPIO17  | 11     | To GND; active-LOW with internal pull-up |
| LED Red     | GPIO18  | 12     | Through 330Ω resistor                   |
| LED Green   | GPIO27  | 13     | Through 330Ω resistor                   |
| LED Common  | GND     | —      | Assumes common-cathode LED              |
| OLED SDA    | GPIO2   | 3      | I²C                                     |
| OLED SCL    | GPIO3   | 5      | I²C                                     |
| OLED VDD    | 3V3     | 1      | Power                                   |
| OLED GND    | GND     | —      | Ground                                  |

> If using a **common-anode** LED, set `COMMON_CATHODE=False` in `pi/state_button_oled.py`.

---

## 1) Deploy the contract (Hardhat)

**Prereqs**: Node.js (LTS), npm, Base Sepolia test ETH for your deployer.

```bash
cd chain
cp .env.example .env
# Edit .env with:
# PRIVATE_KEY=0xyour_private_key   (no quotes)
# ETHERSCAN_API_KEY=your_key        (for verification; optional)

npm i
npm run compile
npm run deploy:base-sepolia
# Copy the "Switch deployed to: 0x..." address
```

**Verify (optional)**
```bash
npm run verify:base-sepolia -- <DEPLOYED_ADDRESS> false
```
The Hardhat config uses:
- RPC: `https://sepolia.base.org`
- Chain ID: `84532`
- Ethers v6 + `@nomicfoundation/hardhat-verify` (Basescan endpoints configured)

**Files**
- `chain/contracts/Switch.sol` — owner-only toggle with `readState()` and events.
- `chain/scripts/deploy.js` — deploy script.

---

## 2) Configure & run the Pi app

**Enable I²C on the Pi**
```
sudo apt install -y raspi-config i2c-tools
sudo raspi-config  → Interface Options → I2C → Enable
i2cdetect -y 1          # OLED typically appears as 0x3C
```

**Install System Packages and configure**
```
sudo apt install -y gpiod python3-libgpiod python3-pip python3-venv
sudo adduser $USER gpio
sudo adduser $USER i2c
newgrp gpio
newgrp i2c
```

**Install Python deps**
```bash
python3 -m venv .venv --system-site-packages && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Pi environment**
```bash
cd pi
cp .env.example .env
# Edit .env with:
# PRIVATE_KEY=0xyour_owner_key
# CONTRACT_ADDRESS=0xDeployedSwitchAddress
# (RPC_URL, CHAIN_ID, MAX_FEE_GWEI, MAX_PRIORITY_FEE_GWEI have sensible defaults)
```

**Run**
```bash
cd pi
python3 state_button_oled.py
```
**What you should see**

* OLED shows the current state.
* Button press: OLED “Toggle” → tx hash prefix → “Confirmed block …”.
* LED: **GREEN = ON**, **RED = OFF** (it stays set after each toggle).

---

## Troubleshooting

* **`i2cdetect` shows nothing**: Recheck `dtparam=i2c_arm=on`, wiring (SDA=GPIO2/pin3, SCL=GPIO3/pin5), and that `i2c-dev` is in `/etc/modules-load.d/i2c.conf`.
* **GPIO permission errors**: Confirm `groups` contains `gpio` and `i2c`. If not, log out/in.
* **libgpiod v1 tools**: CLI tests must put options **before** chip:

  ```bash
  gpioset -m time -u 500000 gpiochip4 18=1
  gpioset -m time -u 500000 gpiochip4 27=1
  ```
* **LED color wrong**: Ensure your LED is **common cathode** (shared GND) and `COMMON_CATHODE=True` in the script; each color needs a 220–330 Ω resistor.
* **RPC lag**: The script reads at the receipt block and then polls `latest` until it matches; if still flaky, try another RPC endpoint.

---

## Quick reference

**Deploy (chain)**
```bash
cd chain && npm i && npm run compile && npm run deploy:base-sepolia
```

**Run on Pi**
```bash
cd pi && sudo -E env "PATH=$PATH" python3 state_button_oled.py
```

---

🧠 Built with purpose by Omniacs.DAO • Back us with $IACS → 0x46e69Fa9059C3D5F8933CA5E993158568DC80EBf (Base)


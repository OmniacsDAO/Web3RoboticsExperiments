# TokenGate — On-chain pulse → Pi motion

A tiny end-to-end demo: deposit ERC-20 into a contract on Base Sepolia → the contract emits a `GatePulse(value, from, amount, timestamp)` event → a Raspberry Pi listener moves a servo and toggles LEDs for `value` seconds.

- **Chain** (`TokenGate/chain/`): Hardhat project that deploys:
  - `TokenGateToken` — simple ERC-20 (1,000,000 supply to deployer).
  - `TokenGate` — accepts deposits of the token and emits `GatePulse`.
- **Pi** (`TokenGate/pi/`): Python app that follows `GatePulse` logs and animates an OLED + LEDs + servo.

## Folder layout
```

TokenGate/
├─ chain/      # Hardhat project (contracts, deploy, verify)
└─ pi/         # Raspberry Pi listener (GPIO + OLED + Web3)

````

## Quickstart

### 1) Deploy contracts on Base Sepolia
```bash
cd chain
npm i
npm run compile
npm run deploy:base-sepolia
# (Optional) Verify
npm run verify:base-sepolia -- <TOKEN_ADDR>
npm run verify:base-sepolia -- <GATE_ADDR> <TOKEN_ADDR>
````

### 2) Drive the contract from Hardhat console

```bash
npx hardhat --network base-sepolia console
> const t = await ethers.getContractAt("TokenGateToken", "<TOKEN_ADDR>");
> const g = await ethers.getContractAt("TokenGate",       "<GATE_ADDR>");
> await t.approve(g.target ?? g.address, ethers.parseUnits("500000", 18));
> await g.deposit(ethers.parseUnits("910", 18)); // emits GatePulse( floor(910/100)=9 )
```

### 3) Run the Raspberry Pi listener

```bash
cd ../pi
python3 -m venv .venv --system-site-packages && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env  # set RPCURL + GATE_ADDRESS
python3 tokengate_pi.py
```

## How it works

* `TokenGate.deposit(amount)` pulls approved tokens and computes:

  ```
  value = floor(amount / (100 * 10^decimals))
  ```

  then emits `GatePulse(value, from, amount, timestamp)`.
* The Pi app streams logs from `GATE_ADDRESS` and:

  * Shows status on 128×64 SSD1306 OLED (I²C @ `0x3C`).
  * Toggles **red/green LEDs** and runs a **servo** for `value` seconds.

---

🧠 Built with purpose by Omniacs.DAO • Back us with $IACS → 0x46e69Fa9059C3D5F8933CA5E993158568DC80EBf (Base)
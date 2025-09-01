# TokenGate / chain (Hardhat)

Deploys and verifies two contracts on Base Sepolia:

- **TokenGateToken** — ERC-20 with 1,000,000 supply minted to deployer.
- **TokenGate** — takes deposits of that token and emits `GatePulse`.

## Prereqs

- Node 18+ and NPM
- A funded Base Sepolia account (for gas)
- `.env` with deployer key + BaseScan/Etherscan API key:
  ```ini
  PRIVATE_KEY="0xyour_deployer_key"
  ETHERSCAN_API_KEY="your_basescan_or_etherscan_key"
````

* Network is preconfigured in Hardhat for **base-sepolia** (url `https://sepolia.base.org`, chainId 84532) and uses `PRIVATE_KEY`.

NPM scripts provided: `compile`, `deploy:base-sepolia`, `verify:base-sepolia`.&#x20;

## Install & Compile

```bash
npm i
npm run compile
```

## Deploy (Base Sepolia)

```bash
npm run deploy:base-sepolia
# sample output:
#   Deployer: 0x...
#   TokenGateToken: 0xTOKEN...
#   TokenGate:      0xGATE...
```

## Verify on BaseScan

```bash
# Token (no constructor args)
npm run verify:base-sepolia -- 0xTOKEN...

# Gate (constructor = token address)
npm run verify:base-sepolia -- 0xGATE... 0xTOKEN...
```

## Interact via Hardhat console

```bash
npx hardhat --network base-sepolia console
> const t = await ethers.getContractAt("TokenGateToken", "0xTOKEN...");
> const g = await ethers.getContractAt("TokenGate", "0xGATE...");
> await t.approve(g.target ?? g.address, ethers.parseUnits("500000", 18));
> await g.deposit(ethers.parseUnits("910", 18)); // GatePulse(9, ...)
```

## Event & Math

* Event: `GatePulse(uint256 value, address from, uint256 amount, uint256 timestamp)`
* `value = floor(amount / (100 * 10^decimals))`  → the Pi uses this to run the servo for `value` seconds.

## Files of interest

* `contracts/TokenGateToken.sol` — minimal ERC-20 (OpenZeppelin).
* `contracts/TokenGate.sol` — deposit + `GatePulse`.
* `scripts/deploy.js` — deploys Token first, then Gate (token address passed to Gate).
* `hardhat.config.js` — Base Sepolia network + Etherscan verify settings.

---

🧠 Built with purpose by Omniacs.DAO • Back us with $IACS → 0x46e69Fa9059C3D5F8933CA5E993158568DC80EBf (Base)
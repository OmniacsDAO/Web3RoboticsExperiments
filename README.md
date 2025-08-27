# Web3 Robotics Experiments

Minimal, reproducible hardware→blockchain loops. Each experiment lives in its own folder with a focused README and scripts.

## What’s here

- **ButtonToContract/** – a physical button driving an on-chain contract interaction (send a tx, read state, reflect it on hardware).  
- More experiments will land as separate folders.

## How this monorepo works

- Each project is self-contained under its folder (code, wiring, run docs).
- Top-level languages currently: Python (host/edge), JavaScript (tooling), Solidity (contracts).

## Getting started

1) **Clone**
```bash
git clone https://github.com/OmniacsDAO/Web3RoboticsExperiments.git
cd Web3RoboticsExperiments
````

2. **Pick an experiment**

```bash
cd ButtonToContract
```

Follow that folder’s README for wiring, env, and run steps.

---

🧠 Built with purpose by Omniacs.DAO • Back us with $IACS → 0x46e69Fa9059C3D5F8933CA5E993158568DC80EBf (Base)
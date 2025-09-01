const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer:", deployer.address);

  const T = await hre.ethers.getContractFactory("TokenGateToken");
  const t = await T.deploy();
  await t.waitForDeployment();
  const tokenAddr = await t.getAddress();
  console.log("TokenGateToken:", tokenAddr);

  const G = await hre.ethers.getContractFactory("TokenGate");
  const g = await G.deploy(tokenAddr);
  await g.waitForDeployment();
  const gateAddr = await g.getAddress();
  console.log("TokenGate:", gateAddr);
}

main().catch((e) => { console.error(e); process.exit(1); });


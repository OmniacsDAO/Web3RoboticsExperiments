// scripts/deploy.js
const { ethers, artifacts } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  const net = await ethers.provider.getNetwork();
  console.log("Network:", net.chainId);
  console.log("Deploying with:", deployer.address);

  // Deploy
  const sw = await ethers.deployContract("Switch", [false]); // start OFF
  await sw.waitForDeployment();
  const addr = await sw.getAddress();
  console.log("Switch deployed to:", addr);

  // Sanity: confirm code exists at addr
  const code = await ethers.provider.getCode(addr);
  console.log("Code size (bytes):", (code.length - 2) / 2);

  // Read via the deployed instance (avoids ABI/address mismatch)
  console.log("Owner:", await sw.owner());
  console.log("readState():", await sw.readState());

  // (Optional) If you prefer re-attaching via ABI:
  // const abi = (await artifacts.readArtifact("Switch")).abi;
  // const sw2 = new ethers.Contract(addr, abi, deployer);
  // console.log("Owner (re-attached):", await sw2.owner());
  // console.log("readState() (re-attached):", await sw2.readState());
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

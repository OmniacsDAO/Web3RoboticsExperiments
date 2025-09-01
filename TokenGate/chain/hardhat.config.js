require("dotenv").config();
require("@nomicfoundation/hardhat-ethers");
require("@nomicfoundation/hardhat-verify");
require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: { version: "0.8.23", settings: { optimizer: { enabled: true, runs: 200 } } },
  networks: {
    "base-sepolia": {
      url: "https://sepolia.base.org",
      chainId: 84532,
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
    },
  },
  // V2 style: single key
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY,   // get an Etherscan key
  },
};

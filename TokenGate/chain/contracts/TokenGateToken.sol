// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title TokenGateToken - 1,000,000 supply ERC20 minted to deployer
contract TokenGateToken is ERC20, Ownable {
    constructor() ERC20("TokenGateToken", "TGT") Ownable(msg.sender) {
        // 1,000,000 * 10^18 to deployer
        _mint(msg.sender, 1_000_000 * 10 ** decimals());
    }
}

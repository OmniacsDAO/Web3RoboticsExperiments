// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title TokenGate - emits a pulse value on token deposits
/// @notice Users must `approve` this contract then call `deposit(amount)`.
contract TokenGate is Ownable {
    IERC20 public immutable token;
    uint8  public immutable tokenDecimals;

    event GatePulse(uint256 value, address indexed from, uint256 amount, uint256 timestamp);

    constructor(address token_) Ownable(msg.sender) {
        require(token_ != address(0), "token=0");
        token = IERC20(token_);
        tokenDecimals = IERC20Metadata(token_).decimals();
    }

    /// @notice Pull tokens from sender, then emit GatePulse with floor(amount / 100 tokens).
    function deposit(uint256 amount) external {
        require(amount > 0, "amount=0");
        require(token.transferFrom(msg.sender, address(this), amount), "transferFrom failed");

        uint256 unit100 = 100 * (10 ** tokenDecimals); // e.g., 100e18
        uint256 value   = amount / unit100;            // integer division floors

        emit GatePulse(value, msg.sender, amount, block.timestamp);
    }

    /// @notice Helper for UI/tests: pure math, no transfer.
    function quote(uint256 amount) external view returns (uint256) {
        uint256 unit100 = 100 * (10 ** tokenDecimals);
        return amount / unit100;
    }

    /// @notice Owner can sweep stuck tokens (demo convenience).
    function sweep(address to, uint256 amt) external onlyOwner {
        require(token.transfer(to, amt), "sweep failed");
    }
}


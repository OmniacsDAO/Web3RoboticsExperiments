// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

/// @title Owner-only ON/OFF switch with a string readout
contract Switch {
    address public immutable owner;
    bool private isOn;

    event StateChanged(bool newState);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(bool _initial) {
        owner = msg.sender;
        isOn = _initial;
        emit StateChanged(isOn);
    }

    function readState() external view returns (string memory) {
        return isOn ? "ON" : "OFF";
    }

    function changeState() external onlyOwner {
        isOn = !isOn;
        emit StateChanged(isOn);
    }
}


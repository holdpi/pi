// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Treasury, IV2Factory, IV2Router, IV2Pair} from "./common/Treasury.sol";

/// @notice The shared treasury with fixed 70/15/10/5 PI revenue allocations.
contract PiTreasury is Treasury {
    function initialize(
        address token_,
        address quote_,
        address rewards_,
        address operations_,
        address router_
    ) external initializer {
        _initializeTreasury(token_, quote_, rewards_, operations_, router_);
    }
    function _allocationBps(
        uint256 bucket
    ) internal pure override returns (uint256) {
        return [uint256(7000), 1500, 1000, 500][bucket];
    }
    function _error(
        string memory reason
    ) internal pure override returns (string memory) {
        return string.concat("PI: ", reason);
    }
}

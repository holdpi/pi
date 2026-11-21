// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {
    Treasury,
    IV2Factory as IHoldV2Factory,
    IV2Router as IHoldV2Router,
    IV2Pair as IHoldV2Pair
} from "../common/Treasury.sol";

/// @notice The shared treasury with allocations fixed during initialization.
contract HoldTreasury is Treasury {
    uint16[4] public splitBps;

    function initialize(
        address token_,
        address quote_,
        address rewards_,
        address operations_,
        address router_,
        uint16[] memory split_
    ) external initializer {
        _initializeTreasury(token_, quote_, rewards_, operations_, router_);
        require(split_.length == 4, "HOLD: split length");
        uint256 total;
        for (uint256 i; i < 4; ++i) {
            total += split_[i];
            splitBps[i] = split_[i];
        }
        require(total == 10000, "HOLD: split total");
    }
    function _allocationBps(
        uint256 bucket
    ) internal view override returns (uint256) {
        return splitBps[bucket];
    }
    function _error(
        string memory reason
    ) internal pure override returns (string memory) {
        return string.concat("HOLD: ", reason);
    }
}

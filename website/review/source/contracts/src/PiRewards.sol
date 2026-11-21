// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {RewardLedger, IWrappedBNB} from "./common/RewardLedger.sol";
import {PiRates} from "./PiRates.sol";

/// @notice The shared reward ledger with the fixed PI acquisition-age policy.
contract PiRewards is RewardLedger {
    uint256 public constant ROUND = 15 minutes;

    function initialize(
        address token_,
        address quote_,
        address treasury_
    ) external initializer {
        _initializeLedger(token_, quote_, treasury_);
    }
    function _sellRate(uint256 age) internal pure override returns (uint256) {
        return PiRates.sell(age);
    }
    function _rewardWeight(
        uint256 age
    ) internal pure override returns (uint256) {
        return PiRates.weight(age);
    }
    function _roundSeconds() internal pure override returns (uint256) {
        return ROUND;
    }
    function _error(
        string memory reason
    ) internal pure override returns (string memory) {
        return string.concat("PI: ", reason);
    }
}

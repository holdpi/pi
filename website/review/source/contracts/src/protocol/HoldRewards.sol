// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {
    RewardLedger,
    IWrappedBNB as IHoldWrappedBNB
} from "../common/RewardLedger.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

/// @notice The shared reward ledger with initialization-bound daily policy tables.
contract HoldRewards is RewardLedger {
    uint256 public ROUND;
    uint256 public minFunding;
    uint16[31] public sellBps;
    uint16[31] public weightBps;

    function initialize(
        address token_,
        address quote_,
        address treasury_,
        uint16[] memory sell_,
        uint16[] memory weight_,
        uint32 round_,
        uint256 min_
    ) external initializer {
        _initializeLedger(token_, quote_, treasury_);
        require(
            sell_.length == 31 &&
                weight_.length == 31 &&
                round_ >= 60 &&
                round_ <= 86400,
            "HOLD: policy"
        );
        require(
            weight_[0] == 0 && weight_[30] >= 10000 && weight_[30] <= 50000,
            "HOLD: weight"
        );
        for (uint256 i; i < 31; ++i) {
            require(
                sell_[i] <= 1000 && (i == 0 || sell_[i] <= sell_[i - 1]),
                "HOLD: sell curve"
            );
            require(
                i == 0 || weight_[i] >= weight_[i - 1],
                "HOLD: weight curve"
            );
            sellBps[i] = sell_[i];
            weightBps[i] = weight_[i];
        }
        ROUND = round_;
        minFunding = min_;
    }

    function _sellRate(uint256 age) internal view override returns (uint256) {
        return sellBps[Math.min(30, age)];
    }
    function _rewardWeight(
        uint256 age
    ) internal view override returns (uint256) {
        return weightBps[Math.min(30, age)];
    }
    function _roundSeconds() internal view override returns (uint256) {
        return ROUND;
    }
    function _minimumFunding() internal view override returns (uint256) {
        return minFunding;
    }
    function _error(
        string memory reason
    ) internal pure override returns (string memory) {
        return string.concat("HOLD: ", reason);
    }
}

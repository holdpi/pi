// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @notice One ABI tuple shared by the builder, token module and validator.
library HoldConfig {
    struct Config {
        address core;
        address rewardsImplementation;
        address treasuryImplementation;
        address router;
        address operations;
        uint16 buyBps;
        uint16[] sellBps;
        uint16[] weightBps;
        uint32 roundSeconds;
        uint256 minFunding;
        uint16[] splitBps;
    }
    function validate(Config memory c) internal pure {
        require(c.buyBps <= 1000, "HOLD: buy cap");
        require(
            c.sellBps.length == 31 && c.weightBps.length == 31,
            "HOLD: 31 days"
        );
        require(
            c.weightBps[0] == 0 &&
                c.weightBps[30] >= 10000 &&
                c.weightBps[30] <= 50000,
            "HOLD: reward bounds"
        );
        for (uint256 i; i < 31; ++i) {
            require(c.sellBps[i] <= 1000, "HOLD: sell cap");
            if (i > 0) {
                require(
                    c.sellBps[i] <= c.sellBps[i - 1],
                    "HOLD: decreasing sell"
                );
                require(
                    c.weightBps[i] >= c.weightBps[i - 1],
                    "HOLD: increasing weight"
                );
            }
        }
        require(
            c.roundSeconds >= 60 && c.roundSeconds <= 1 days,
            "HOLD: cadence"
        );
        require(c.minFunding <= 1_000_000 ether, "HOLD: funding threshold");
        require(c.splitBps.length == 4, "HOLD: split length");
        uint256 total;
        for (uint256 i; i < 4; ++i) total += c.splitBps[i];
        require(total == 10000, "HOLD: split total");
        require(c.operations != address(0), "HOLD: operations address");
    }
}

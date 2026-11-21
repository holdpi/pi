// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {OpenFourToken} from "../../vendor/openfour/token/OpenFourToken.sol";
import {OpenFourTypes} from "../../vendor/openfour/libraries/OpenFourTypes.sol";
import {RewardLedger} from "./RewardLedger.sol";
import {Treasury, IV2Router, IV2Factory, IV2Pair} from "./Treasury.sol";

/// @notice Shared transfer accounting for acquisition-age taxes and rewards.
/// @dev Ordinary transfers settle the bounded ledger without invoking a DEX or a recipient.
abstract contract AcquisitionToken is OpenFourToken {
    address public core;
    address public canonicalPool;
    RewardLedger public rewards;
    Treasury public treasury;
    event BondingTaxNotified(uint256 quoteTax, bool isBuy);

    function _registerPool(address router, address quoteAsset) internal {
        address factory = IV2Router(router).factory();
        canonicalPool = IV2Factory(factory).getPair(address(this), quoteAsset);
        if (canonicalPool == address(0)) {
            canonicalPool = IV2Factory(factory).createPair(
                address(this),
                quoteAsset
            );
        }
        require(
            canonicalPool.code.length > 0 &&
                IV2Pair(canonicalPool).totalSupply() == 0,
            _error("initial pool")
        );
        migratedPools[canonicalPool] = true;
        emit MigratedPoolUpdated(canonicalPool, true);
    }
    function _excluded(address who) internal view returns (bool) {
        return
            who == address(0) ||
            who == address(0xdEaD) ||
            who == vault ||
            who == core ||
            who == migrateModule ||
            who == address(this) ||
            who == address(rewards) ||
            who == address(treasury) ||
            migratedPools[who];
    }
    function isExcluded(address who) external view returns (bool) {
        return _excluded(who);
    }
    function _transfer(
        address from,
        address to,
        uint256 amount
    ) internal override {
        // Never call a router, recipient or payout strategy from ordinary exits.
        if (amount == 0 || from == to) {
            super._transfer(from, to, amount);
            return;
        }
        bool fromExcluded = _excluded(from);
        bool toExcluded = _excluded(to);
        bool settlement =
            tokenPhase == OpenFourTypes.Phase.Trading &&
                msg.sender == core &&
                to == vault;
        bool internalProcessing =
            (from == address(treasury) || to == address(treasury)) &&
                (migratedPools[from] || migratedPools[to]) &&
                treasury.processing();
        uint256 fee;
        if (!fromExcluded) {
            fee = rewards.debit(from, amount);
            if (settlement) fee = 0; // the Core collects the quoted BNB tax once
        } else if (migratedPools[from] && !toExcluded && !internalProcessing) {
            fee = (amount * _buyBps()) / 10000;
        }
        if (internalProcessing) fee = 0;
        if (fee > 0) super._transfer(from, address(treasury), fee);
        uint256 net = amount - fee;
        super._transfer(from, to, net);
        if (!toExcluded) rewards.credit(to, net);
    }
    function exitFeeBps(
        address holder,
        uint256 amount
    ) external view returns (uint256) {
        return rewards.exitBps(holder, amount);
    }
    function onBondingTrade(uint256 amount, bool isBuy) external onlyVault {
        // The TradeModule directs tax to the treasury. Only measured receipts
        // are allocated later. A notification never creates unfunded rewards.
        emit BondingTaxNotified(amount, isBuy);
    }
    function onMigrate() external onlyMigrate {
        /* no swaps inside migration */
    }
    function burnTreasury(uint256 amount) external {
        require(msg.sender == address(treasury), _error("treasury only"));
        _burn(msg.sender, amount);
    }
    function _buyBps() internal view virtual returns (uint256);
    function _error(
        string memory reason
    ) internal pure virtual returns (string memory);
}

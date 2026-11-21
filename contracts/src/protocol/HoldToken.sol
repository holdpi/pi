// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {HoldConfig} from "./HoldConfig.sol";
import {Clones} from "@openzeppelin/contracts/proxy/Clones.sol";
import {OpenFourToken} from "../../vendor/openfour/token/OpenFourToken.sol";
import {OpenFourTypes} from "../../vendor/openfour/libraries/OpenFourTypes.sol";
import {HoldRewards} from "./HoldRewards.sol";
import {HoldTreasury, IHoldV2Router, IHoldV2Factory, IHoldV2Pair} from "./HoldTreasury.sol";

/// @notice Configurable OpenFour token. Policy is fixed during each initialization.
/// @dev Registry-controlled beacon upgrades are an external trust boundary.
contract HoldToken is OpenFourToken {
    uint256 public buyFeeRate;
    uint256 public sellFeeRate;
    bytes32 public policyHash;
    address public core;
    address public canonicalPool;
    HoldRewards public rewards;
    HoldTreasury public treasury;
    event BondingTaxNotified(uint256 quoteTax, bool isBuy);

    function initialize(InitArgs calldata c) external override initializer {
        require(msg.sender == c.tokenModule, "HOLD: token module only");
        require(
            c.maxSupply > 0 && c.maxSupply <= 1e30 && c.quoteAsset.code.length > 0,
            "HOLD: supply or quote"
        );
        HoldConfig.Config memory p = abi.decode(c.tokenParams, (HoldConfig.Config));
        HoldConfig.validate(p);
        buyFeeRate = p.buyBps;
        sellFeeRate = p.sellBps[0];
        policyHash = keccak256(c.tokenParams);
        require(
            p.core.code.length > 0 &&
                p.rewardsImplementation.code.length > 0 &&
                p.treasuryImplementation.code.length > 0,
            "HOLD: implementations"
        );
        core = p.core;
        rewards = HoldRewards(payable(Clones.clone(p.rewardsImplementation)));
        treasury = HoldTreasury(Clones.clone(p.treasuryImplementation));
        rewards.initialize(address(this), c.quoteAsset, address(treasury), p.sellBps, p.weightBps, p.roundSeconds, p.minFunding);
        treasury.initialize(
            address(this),
            c.quoteAsset,
            address(rewards),
            p.operations,
            p.router, p.splitBps
        );
        address factory = IHoldV2Router(p.router).factory();
        canonicalPool = IHoldV2Factory(factory).getPair(
            address(this),
            c.quoteAsset
        );
        if (canonicalPool == address(0))
            canonicalPool = IHoldV2Factory(factory).createPair(
                address(this),
                c.quoteAsset
            );
        require(
            canonicalPool.code.length > 0 &&
                IHoldV2Pair(canonicalPool).totalSupply() == 0,
            "HOLD: initial pool"
        );
        migratedPools[canonicalPool] = true;
        emit MigratedPoolUpdated(canonicalPool, true);
        __OpenFourToken_init(c);
    }
    function _descriptorTag() internal pure override returns (string memory) {
        return "token.holdpi_configurable";
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
            fee = (amount * buyFeeRate) / 10000;
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
        require(msg.sender == address(treasury), "HOLD: treasury only");
        _burn(msg.sender, amount);
    }
}

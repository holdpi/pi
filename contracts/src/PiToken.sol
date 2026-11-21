// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Clones} from "@openzeppelin/contracts/proxy/Clones.sol";
import {AcquisitionToken} from "./common/AcquisitionToken.sol";
import {PiRewards} from "./PiRewards.sol";
import {PiTreasury} from "./PiTreasury.sol";

/// @notice PI OpenFour token. Taxes are immutable in this implementation.
/// @dev Registry-controlled beacon upgrades are an external trust boundary.
contract PiToken is AcquisitionToken {
    struct Config {
        address core;
        address rewardsImplementation;
        address treasuryImplementation;
        address router;
        address operations;
    }
    uint256 public constant SUPPLY = 1_000_000_000 ether;
    uint256 public constant buyFeeRate = 500;
    uint256 public constant sellFeeRate = 1000;

    function initialize(InitArgs calldata c) external override initializer {
        require(msg.sender == c.tokenModule, "PI: token module only");
        require(
            c.maxSupply == SUPPLY && c.quoteAsset.code.length > 0,
            "PI: supply or quote"
        );
        Config memory p = abi.decode(c.tokenParams, (Config));
        require(
            p.core.code.length > 0 &&
                p.rewardsImplementation.code.length > 0 &&
                p.treasuryImplementation.code.length > 0,
            "PI: implementations"
        );
        core = p.core;
        rewards = PiRewards(payable(Clones.clone(p.rewardsImplementation)));
        treasury = PiTreasury(Clones.clone(p.treasuryImplementation));
        PiRewards(payable(address(rewards))).initialize(
            address(this),
            c.quoteAsset,
            address(treasury)
        );
        PiTreasury(address(treasury)).initialize(
            address(this),
            c.quoteAsset,
            address(rewards),
            p.operations,
            p.router
        );
        _registerPool(p.router, c.quoteAsset);
        __OpenFourToken_init(c);
    }
    function _descriptorTag() internal pure override returns (string memory) {
        return "token.pi_acquisition_age";
    }
    function _buyBps() internal pure override returns (uint256) {
        return buyFeeRate;
    }
    function _error(
        string memory reason
    ) internal pure override returns (string memory) {
        return string.concat("PI: ", reason);
    }
}

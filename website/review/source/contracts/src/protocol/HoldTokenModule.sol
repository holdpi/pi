// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {IOpenFourTokenModule} from "../../vendor/openfour/interfaces/IOpenFourTokenModule.sol";
import {OpenFourToken} from "../../vendor/openfour/token/OpenFourToken.sol";
import {IOpenFourModuleSchema} from "../../vendor/openfour/interfaces/IOpenFourModuleSchema.sol";
import {
    OpenFourTypes,
    ParamDescriptor,
    ModuleEncodeSchema
} from "../../vendor/openfour/libraries/OpenFourTypes.sol";
contract HoldTokenModule is IOpenFourTokenModule, IOpenFourModuleSchema {
    address public immutable fourCore;
    bool private created;
    bytes private raw;
    string private version;
    constructor(address core) {
        require(core != address(0), "HOLD: core");
        fourCore = core;
    }
    function createToken(
        address creator,
        address token,
        address vault,
        address curve,
        address trade,
        address migrate,
        address customData,
        OpenFourTypes.TokenCreateParams calldata p,
        string calldata tokenVersion,
        string calldata moduleVersion
    ) external returns (uint256, string memory, string memory) {
        require(msg.sender == fourCore && !created, "HOLD: creation authority");
        created = true;
        raw = p.tokenParams;
        version = moduleVersion;
        OpenFourToken(token).initialize(
            OpenFourToken.InitArgs(
                p.requestId,
                p.name,
                p.symbol,
                vault,
                p.maxSupply,
                p.tokenUri,
                curve,
                trade,
                migrate,
                address(this),
                customData,
                creator,
                p.quoteAsset,
                p.tokenParams,
                tokenVersion
            )
        );
        return (p.maxSupply, p.name, p.symbol);
    }
    function getInitParams() external view returns (bytes memory) {
        return raw;
    }
    function descriptor()
        external
        view
        returns (bytes8, string memory, string memory)
    {
        return (
            bytes8(keccak256("module.token.holdpi_configurable")),
            "module.token.holdpi_configurable",
            version
        );
    }
    function moduleEncodeSchema()
        external
        pure
        returns (ModuleEncodeSchema memory)
    {
        ParamDescriptor[] memory p = new ParamDescriptor[](11);
        p[0] = ParamDescriptor(
            "core",
            "address",
            0,
            false,
            "OpenFour Core",
            "",
            "",
            "",
            ""
        );
        p[1] = ParamDescriptor(
            "rewardsImplementation",
            "address",
            0,
            false,
            "Rewards implementation",
            "",
            "",
            "",
            ""
        );
        p[2] = ParamDescriptor(
            "treasuryImplementation",
            "address",
            0,
            false,
            "Treasury implementation",
            "",
            "",
            "",
            ""
        );
        p[3] = ParamDescriptor(
            "router",
            "address",
            0,
            false,
            "PancakeSwap V2 router",
            "",
            "",
            "",
            ""
        );
        p[4] = ParamDescriptor(
            "operations",
            "address",
            0,
            false,
            "Operations recipient",
            "",
            "",
            "",
            ""
        );
        p[5] = ParamDescriptor(
            "buyBps",
            "uint16",
            0,
            false,
            "Buy tax in basis points",
            "500",
            "",
            "",
            ""
        );
        p[6] = ParamDescriptor(
            "sellBps",
            "uint16[]",
            0,
            false,
            "Daily sell curve, days 0 to 30",
            "",
            "",
            "",
            ""
        );
        p[7] = ParamDescriptor(
            "weightBps",
            "uint16[]",
            0,
            false,
            "Daily reward weights, 10000 = 1x",
            "",
            "",
            "",
            ""
        );
        p[8] = ParamDescriptor(
            "roundSeconds",
            "uint32",
            0,
            false,
            "Minimum seconds between funded rounds",
            "900",
            "",
            "",
            ""
        );
        p[9] = ParamDescriptor(
            "minFunding",
            "uint256",
            0,
            false,
            "Minimum round funding in wei",
            "0",
            "",
            "",
            ""
        );
        p[10] = ParamDescriptor(
            "splitBps",
            "uint16[]",
            0,
            false,
            "Holders, burn, liquidity, operations in bps",
            "7000,1500,1000,500",
            "",
            "",
            ""
        );
        return ModuleEncodeSchema("token", 1, p);
    }
}

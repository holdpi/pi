// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {PancakeMigration} from "../common/PancakeMigration.sol";
import {IOpenFourModuleSchema} from "../../vendor/openfour/interfaces/IOpenFourModuleSchema.sol";
import {
    ParamDescriptor,
    ModuleEncodeSchema
} from "../../vendor/openfour/libraries/OpenFourTypes.sol";

/// @notice Configurable preset descriptor and encoding schema for the shared implementation.
contract HoldMigrateModule is PancakeMigration, IOpenFourModuleSchema {
    function _descriptorTag() internal pure override returns (string memory) {
        return "module.migrate.holdpi_v2";
    }
    function moduleEncodeSchema()
        external
        pure
        returns (ModuleEncodeSchema memory)
    {
        return ModuleEncodeSchema("migrate", 1, new ParamDescriptor[](0));
    }
}

// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {PancakeMigration} from "./common/PancakeMigration.sol";

/// @notice Fixed PI descriptor for the shared PancakeSwap migration.
contract PiMigrateModule is PancakeMigration {
    function _descriptorTag() internal pure override returns (string memory) {
        return "module.migrate.pi_v2";
    }
}

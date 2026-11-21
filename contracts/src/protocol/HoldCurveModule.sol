// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {VirtualReserveCurve} from "../common/VirtualReserveCurve.sol";
import {IOpenFourModuleSchema} from "../../vendor/openfour/interfaces/IOpenFourModuleSchema.sol";
import {
    ParamDescriptor,
    ModuleEncodeSchema
} from "../../vendor/openfour/libraries/OpenFourTypes.sol";

/// @notice Configurable preset descriptor and encoding schema for the shared implementation.
contract HoldCurveModule is VirtualReserveCurve, IOpenFourModuleSchema {
    function _descriptorTag() internal pure override returns (string memory) {
        return "module.curve.holdpi_virtual";
    }
    function moduleEncodeSchema()
        external
        pure
        returns (ModuleEncodeSchema memory)
    {
        ParamDescriptor[] memory p = new ParamDescriptor[](2);
        p[0] = ParamDescriptor(
            "virtualToken",
            "uint256",
            18,
            false,
            "Virtual token reserve",
            "1000000000",
            "Must exceed sale inventory",
            "0",
            "1000000000000"
        );
        p[1] = ParamDescriptor(
            "virtualQuote",
            "uint256",
            18,
            false,
            "Virtual BNB reserve",
            "100",
            "Pricing reserve, not treasury funds",
            "0",
            "1000000000000"
        );
        return ModuleEncodeSchema("curve", 1, p);
    }
}

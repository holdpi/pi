// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
import {VirtualReserveCurve} from "./common/VirtualReserveCurve.sol";

/// @notice Fixed PI descriptor for the shared virtual-reserve curve.
contract PiCurveModule is VirtualReserveCurve {
    function _descriptorTag() internal pure override returns (string memory) {
        return "module.curve.pi_virtual";
    }
}

// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Initializable} from "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {PiRates} from "../PiRates.sol";

interface IWrappedBNB is IERC20 {
    function deposit() external payable;
    function withdraw(uint256) external;
}

/// @notice Bounded acquisition ledger and funded reward indices. No holder loop.
/// @dev The token alone changes balances. Each account and the global active set
/// contain at most 31 daily cohorts. Mature cohorts share one cumulative index.
/// Funding is measured on receipt and claims consume only settled, backed credit.
abstract contract RewardLedger is Initializable, ReentrancyGuard {
    using SafeERC20 for IERC20;
    uint256 public constant PRECISION = 1e36;
    struct Lot {
        uint256 born;
        uint256 amount;
        uint256 paidIndex;
    }
    struct Account {
        uint256 mature;
        uint256 maturePaidIndex;
        uint256 earnedScaled;
        uint256 balance;
        Lot[] lots;
    }
    struct Cohort {
        uint256 amount;
        uint256 index;
        uint256 mergeMatureIndex;
        bool exists;
        bool merged;
    }
    address public token;
    address public treasury;
    IWrappedBNB public quote;
    mapping(address => Account) private accounts;
    mapping(uint256 => Cohort) public cohorts;
    uint256[] private active;
    uint256 public matureAmount;
    uint256 public matureIndex;
    uint256 public funded;
    uint256 public paid;
    uint256 public pending;
    uint256 public roundingScaled;
    uint256 public lastRound;
    event Funded(uint256 received);
    event Distributed(
        uint256 quoteAmount,
        uint256 totalWeight,
        uint256 timestamp
    );
    event Claimed(
        address indexed holder,
        address indexed recipient,
        uint256 amount,
        bool nativeBNB
    );

    constructor() {
        _disableInitializers();
    }
    modifier onlyToken() {
        require(msg.sender == token, _error("token only"));
        _;
    }
    function _initializeLedger(
        address token_,
        address quote_,
        address treasury_
    ) internal onlyInitializing {
        require(
            msg.sender == token_ &&
                token_ != address(0) &&
                quote_.code.length > 0 &&
                treasury_ != address(0),
            _error("bad reward config")
        );
        token = token_;
        quote = IWrappedBNB(quote_);
        treasury = treasury_;
    }
    function _roll() internal {
        uint256 i;
        while (i < active.length) {
            uint256 born = active[i];
            if (PiRates.age(born, block.timestamp) >= 30) {
                Cohort storage cohort = cohorts[born];
                cohort.merged = true;
                cohort.mergeMatureIndex = matureIndex;
                matureAmount += cohort.amount;
                active[i] = active[active.length - 1];
                active.pop();
            } else {
                ++i;
            }
        }
    }
    function _settle(address who) internal returns (Account storage account) {
        _roll();
        account = accounts[who];
        account.earnedScaled +=
            account.mature * (matureIndex - account.maturePaidIndex);
        account.maturePaidIndex = matureIndex;
        uint256 kept;
        uint256 length = account.lots.length;
        for (uint256 i; i < length; ++i) {
            Lot memory lot = account.lots[i];
            Cohort storage cohort = cohorts[lot.born];
            uint256 index = cohort.index;
            if (cohort.merged) index += matureIndex - cohort.mergeMatureIndex;
            account.earnedScaled += lot.amount * (index - lot.paidIndex);
            if (cohort.merged) {
                account.mature += lot.amount;
            } else {
                lot.paidIndex = index;
                account.lots[kept++] = lot;
            }
        }
        while (account.lots.length > kept) account.lots.pop();
    }
    function credit(address who, uint256 amount) external onlyToken {
        if (amount == 0) return;
        Account storage account = _settle(who);
        uint256 born = PiRates.birth(block.timestamp);
        Cohort storage cohort = cohorts[born];
        if (!cohort.exists) {
            cohort.exists = true;
            active.push(born);
        }
        uint256 length = account.lots.length;
        if (length > 0 && account.lots[length - 1].born == born)
            account.lots[length - 1].amount += amount;
        else account.lots.push(Lot(born, amount, cohort.index));
        require(
            account.lots.length <= 31 && active.length <= 31,
            _error("cohort bound")
        );
        account.balance += amount;
        cohort.amount += amount;
    }
    /// @return fee Amount of PI due for this exit, newest acquisition first.
    function debit(
        address who,
        uint256 amount
    ) external onlyToken returns (uint256 fee) {
        Account storage account = _settle(who);
        require(amount <= account.balance, _error("ledger balance"));
        account.balance -= amount;
        uint256 left = amount;
        while (left > 0 && account.lots.length > 0) {
            Lot storage lot = account.lots[account.lots.length - 1];
            uint256 take = Math.min(left, lot.amount);
            fee +=
                (take * _sellRate(PiRates.age(lot.born, block.timestamp))) /
                10000;
            lot.amount -= take;
            cohorts[lot.born].amount -= take;
            left -= take;
            if (lot.amount == 0) account.lots.pop();
        }
        if (left > 0) {
            account.mature -= left;
            matureAmount -= left;
            fee += (left * _sellRate(30)) / 10000;
        }
    }
    /// @notice Quote asset settlement only has whole-bps precision. Round its
    /// weighted rate upward; the error is below one bps of curve quote.
    function exitBps(
        address who,
        uint256 amount
    ) external view returns (uint256) {
        Account storage account = accounts[who];
        require(
            amount > 0 && amount <= account.balance,
            _error("quote amount")
        );
        uint256 left = amount;
        uint256 numerator;
        for (uint256 i = account.lots.length; i > 0 && left > 0;) {
            Lot storage lot = account.lots[--i];
            uint256 take = Math.min(left, lot.amount);
            numerator +=
                take * _sellRate(PiRates.age(lot.born, block.timestamp));
            left -= take;
        }
        numerator += left * _sellRate(30);
        return (numerator + amount - 1) / amount;
    }
    function fund(uint256 amount) external nonReentrant {
        require(msg.sender == treasury, _error("treasury only"));
        uint256 beforeBalance = quote.balanceOf(address(this));
        IERC20(address(quote)).safeTransferFrom(
            msg.sender,
            address(this),
            amount
        );
        uint256 received = quote.balanceOf(address(this)) - beforeBalance;
        require(
            funded + received <= type(uint256).max / PRECISION,
            _error("funding bound")
        );
        funded += received;
        pending += received;
        emit Funded(received);
    }
    function totalWeight() public view returns (uint256 totalWeightUnits) {
        totalWeightUnits = matureAmount * _rewardWeight(30);
        for (uint256 i; i < active.length; ++i) {
            uint256 born = active[i];
            totalWeightUnits +=
                cohorts[born].amount *
                _rewardWeight(PiRates.age(born, block.timestamp));
        }
    }
    function distribute() external nonReentrant returns (uint256 amount) {
        require(
            block.timestamp >= lastRound + _roundSeconds(),
            _error("round not due")
        );
        _roll();
        uint256 totalWeightUnits = totalWeight();
        amount = pending + roundingScaled / PRECISION;
        if (totalWeightUnits == 0 || amount == 0 || amount < _minimumFunding())
            return 0;
        lastRound = block.timestamp;
        pending = 0;
        roundingScaled %= PRECISION;
        uint256 allocated;
        for (uint256 i; i < active.length; ++i) {
            uint256 born = active[i];
            Cohort storage cohort = cohorts[born];
            uint256 delta = Math.mulDiv(
                amount,
                _rewardWeight(PiRates.age(born, block.timestamp)) * PRECISION,
                totalWeightUnits
            );
            cohort.index += delta;
            allocated += cohort.amount * delta;
        }
        uint256 matureDelta = Math.mulDiv(
            amount,
            _rewardWeight(30) * PRECISION,
            totalWeightUnits
        );
        matureIndex += matureDelta;
        allocated += matureAmount * matureDelta;
        roundingScaled += amount * PRECISION - allocated;
        emit Distributed(amount, totalWeightUnits, block.timestamp);
    }
    function claim(
        address payable recipient,
        bool nativeBNB
    ) external nonReentrant returns (uint256 amount) {
        require(
            recipient != address(0) && recipient != address(this),
            _error("recipient")
        );
        Account storage account = _settle(msg.sender);
        amount = account.earnedScaled / PRECISION;
        if (amount == 0) return 0;
        require(amount <= quote.balanceOf(address(this)), _error("backing"));
        account.earnedScaled -= amount * PRECISION;
        paid += amount;
        if (nativeBNB) {
            quote.withdraw(amount);
            (bool ok, ) = recipient.call{value: amount, gas: 50000}("");
            if (!ok) {
                quote.deposit{value: amount}();
                IERC20(address(quote)).safeTransfer(recipient, amount);
                nativeBNB = false;
            }
        } else {
            IERC20(address(quote)).safeTransfer(recipient, amount);
        }
        emit Claimed(msg.sender, recipient, amount, nativeBNB);
    }
    function claimable(address who) external view returns (uint256) {
        Account storage account = accounts[who];
        uint256 scaled =
            account.earnedScaled +
                account.mature * (matureIndex - account.maturePaidIndex);
        for (uint256 i; i < account.lots.length; ++i) {
            Lot storage lot = account.lots[i];
            Cohort storage cohort = cohorts[lot.born];
            uint256 index =
                cohort.index +
                    (cohort.merged ? matureIndex - cohort.mergeMatureIndex : 0);
            scaled += lot.amount * (index - lot.paidIndex);
        }
        return scaled / PRECISION;
    }
    function balanceOf(address who) external view returns (uint256) {
        return accounts[who].balance;
    }
    function lotsOf(address who) external view returns (Lot[] memory) {
        return accounts[who].lots;
    }
    function matureOf(address who) external view returns (uint256) {
        return accounts[who].mature;
    }
    function activeCohorts() external view returns (uint256[] memory) {
        return active;
    }
    receive() external payable {
        require(msg.sender == address(quote), _error("WBNB only"));
    }
    function _sellRate(uint256 age) internal view virtual returns (uint256);
    function _rewardWeight(uint256 age) internal view virtual returns (uint256);
    function _roundSeconds() internal view virtual returns (uint256);
    function _minimumFunding() internal view virtual returns (uint256) {
        return 0;
    }
    function _error(
        string memory reason
    ) internal pure virtual returns (string memory);
}

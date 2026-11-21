const sharedContractSuite = require("./shared/contracts.cjs");
sharedContractSuite({
  fixtures: require("./protocol-fixtures.cjs"),
  label: "Configurable contracts with PI defaults on a BNB fork",
  prefix: "HOLD",
  variant: "Hold",
  weightScale: 10000,
});

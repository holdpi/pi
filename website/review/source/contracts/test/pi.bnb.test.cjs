const sharedContractSuite = require("./shared/contracts.cjs");
sharedContractSuite({
  fixtures: require("./fixtures.cjs"),
  label: "Fixed PI contracts on a BNB fork",
  prefix: "PI",
  variant: "Pi",
  weightScale: 2,
});

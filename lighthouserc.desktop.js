// TC-PERF-01's desktop-preset half -- see lighthouserc.js for the mobile
// (default) preset and fixture-selection rationale.
const base = require("./lighthouserc.js");

module.exports = {
  ci: {
    ...base.ci,
    collect: {
      ...base.ci.collect,
      settings: { preset: "desktop" },
    },
    upload: {
      target: "filesystem",
      outputDir: "./.lighthouseci-desktop",
    },
  },
};

// make test (dd.md §10) runs this against an already-built _site/ served
// by `make serve` in a separate step -- no webServer block here, since CI
// and local runs both start the server explicitly first.
module.exports = {
  testDir: "./tests",
  timeout: 30000,
  reporter: "list",
  use: {
    baseURL: "http://localhost:8098/yahoo-groups-tne-archive/",
  },
};

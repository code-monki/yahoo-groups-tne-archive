const fs = require("fs");
const path = require("path");

module.exports = function (eleventyConfig) {
  // ADR-0017: this repo is served under a GitHub Pages project subpath, not
  // domain root. Every internal link/asset reference must go through the
  // `url` filter (built into Eleventy, honors pathPrefix below) rather than
  // a hand-written absolute path — that discipline is what keeps a future
  // custom-domain switch a config-only change instead of a template rewrite.
  eleventyConfig.addPassthroughCopy("site/css");
  eleventyConfig.addPassthroughCopy("site/js");

  // ADR-0006/FR-27: availability is computed fresh from the attachments/
  // directory at build time -- never stored in data/posts.json -- so that
  // dropping a recovered file in and rebuilding is the entire remediation,
  // with no per-post metadata to also go update. See dd.md §6.
  const ATTACHMENTS_DIR = path.join(__dirname, "attachments");
  eleventyConfig.addFilter("attachmentAvailable", function (postId, filename) {
    return fs.existsSync(path.join(ATTACHMENTS_DIR, postId, filename));
  });
  // Copies a present attachment file into the build output alongside its
  // owning post's page (used by post.njk in Phase 7, once real attachment
  // files exist to test against).
  eleventyConfig.addPassthroughCopy({
    [path.relative(__dirname, ATTACHMENTS_DIR)]: "attachments",
  });

  // Formats an ISO 8601 UTC date_utc value for display -- e.g. "Sun, Nov 16,
  // 2008". The <time datetime="..."> element's machine-readable value uses
  // date_utc directly (DR-3); this filter is only for the human-visible text.
  eleventyConfig.addFilter("formatDate", function (dateUtc) {
    const d = new Date(dateUtc);
    return d.toLocaleDateString("en-US", {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    });
  });

  const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  // "03" -> "March", for browse-year's month listing.
  eleventyConfig.addFilter("monthName", function (monthNum) {
    return MONTH_NAMES[parseInt(monthNum, 10) - 1];
  });
  // date_utc ISO string -> "March 2012", for browse-index's date range and
  // author/topic list rows (coarser than formatDate's full day-level date).
  eleventyConfig.addFilter("monthYear", function (dateUtc) {
    const d = new Date(dateUtc);
    return `${MONTH_NAMES[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  });

  return {
    dir: {
      input: "site",
      includes: "_includes",
      data: "_data",
      output: "_site",
    },
    pathPrefix: "/yahoo-groups-tne-archive/",
    templateFormats: ["njk", "md"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk",
  };
};

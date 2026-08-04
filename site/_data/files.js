// ADR-0018: the Files-section manifest (data/files.json), a distinct thing
// from post attachments -- a shared group repository, not tied to any one
// email. Mirrors posts.js's own pattern: load the committed data once,
// compute derived views, never a second copy of the data. Availability is
// deliberately NOT computed here either, for the same reason posts.js
// doesn't for attachments -- see eleventy.js's `fileAvailable` filter.

const fs = require("fs");
const path = require("path");

const FILES_DATA_PATH = path.join(__dirname, "..", "..", "data", "files.json");

module.exports = function () {
  const manifest = JSON.parse(fs.readFileSync(FILES_DATA_PATH, "utf-8"));
  const postsData = require("./posts.js")();

  // The uploader field is a bare Yahoo handle (e.g. "rogerclarktopaz"),
  // extracted from Yahoo's own notification email -- cross-referenced
  // against every post's author.profile_handle (already resolved from
  // real profile links elsewhere in the archive) so the page can link to
  // that person's real author page and show their display name, not just
  // the raw handle, whenever a match exists.
  const authorByHandle = new Map();
  for (const post of postsData.all) {
    const handle = post.author.profile_handle;
    if (handle && !authorByHandle.has(handle)) {
      authorByHandle.set(handle, { slug: post.author.slug, displayName: post.author.display_name });
    }
  }

  const entries = manifest.map((f) => ({
    ...f,
    uploaderAuthor: authorByHandle.get(f.uploader) || null,
  }));

  // Most-recent-first, matching Home's recentPosts convention.
  entries.sort((a, b) => (a.uploaded_date_utc < b.uploaded_date_utc ? 1 : -1));

  return { all: entries };
};

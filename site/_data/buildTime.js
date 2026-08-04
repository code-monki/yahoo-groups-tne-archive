// Eleventy calls global data functions once per build, not once per page,
// so every sitemap <lastmod> entry gets the same, real build timestamp --
// the honest answer for a frozen archive (ADR-0001) where "last modified"
// only ever means "last time this was rebuilt and deployed," not a
// per-post edit time.
module.exports = () => new Date().toISOString();

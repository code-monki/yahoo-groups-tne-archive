// Front-matter YAML parses once into a single shared object tree, so
// eleventyComputed values written as Nunjucks template strings in
// post.njk's front matter have two problems, both confirmed against the
// real build:
//
// 1. `breadcrumb` (an array of objects) ended up as one shared array
//    reused across every paginated post -- post 6312's breadcrumb showed
//    an unrelated post's subject even though its own <h1> (computed from
//    a plain string, not an array) was correct.
// 2. `title`/`description` (plain strings) get rendered through Nunjucks
//    TWICE -- once to resolve the front-matter template string itself,
//    again when base.njk outputs `{{ title }}` -- so any subject with a
//    quote or ampersand came out double-escaped (`&amp;quot;` instead of
//    `&quot;`). 410 of 4060 posts have such characters in their subject.
//
// JS functions here sidestep both: they return fresh values per page and
// are only ever rendered once, by the layout.
function truncate(text, length) {
  // Collapse whitespace (including newlines) before cutting -- body_text
  // is real multi-paragraph message content, and a raw newline landing
  // inside the truncated result breaks the og:description meta tag's
  // content="..." attribute across multiple lines (confirmed against the
  // real build, post 6835).
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= length) return normalized;
  const cut = normalized.lastIndexOf(" ", length);
  return normalized.slice(0, cut === -1 ? length : cut) + "...";
}

module.exports = {
  eleventyComputed: {
    title: (data) => data.post.subject,
    description: (data) => truncate(data.post.body_text, 160),
    breadcrumb: (data) => [
      { label: "Home", url: "/" },
      { label: data.post.subject },
    ],
  },
};

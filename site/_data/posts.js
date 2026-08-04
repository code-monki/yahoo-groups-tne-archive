// Eleventy global data (dd.md §7.1). Loads the committed canonical dataset
// once per build and computes every derived, build-time-only view templates
// need (by author, by topic, by year/month, by thread) -- per ADR-0001,
// there is exactly one source of truth (data/posts.json); everything here
// is a view over it, never a second copy of the data.
//
// Attachment availability is deliberately NOT computed here -- see
// eleventy.js's `attachmentAvailable` filter, which checks the filesystem
// per-post at render time instead (dd.md §6/§7.1; hld.md §3's corrected
// example) so it's never a value that can go stale between commits.

const fs = require("fs");
const path = require("path");

const DATA_PATH = path.join(__dirname, "..", "..", "data", "posts.json");

// Mirrors pipeline/ids.py's _slugify() exactly, including the length cap --
// see that function's comment for why (a several-hundred-character slug
// from a misextracted field breaking the filesystem, confirmed against the
// real archive).
const SLUG_MAX_LEN = 80;

function slugify(text) {
  const slug = text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, SLUG_MAX_LEN)
    .replace(/^-+|-+$/g, "");
  return slug || "unknown";
}

// Mirrors pipeline/ids.py's resolve_author_slugs() collision rule exactly
// (lowest id in the colliding group, sorted lexically) -- deterministic and
// stable across rebuilds, applied here in JS since topic slugs (unlike
// author slugs) are never precomputed in the Python ETL output.
function resolveSlugs(groups) {
  const baseSlugToKeys = new Map();
  for (const key of groups.keys()) {
    const base = slugify(key);
    if (!baseSlugToKeys.has(base)) baseSlugToKeys.set(base, []);
    baseSlugToKeys.get(base).push(key);
  }
  const slugs = new Map();
  for (const [base, keys] of baseSlugToKeys) {
    if (keys.length === 1) {
      slugs.set(keys[0], base);
      continue;
    }
    const withMinId = keys
      .map((key) => {
        const ids = groups.get(key).map((p) => p.id).sort();
        return [ids[0], key];
      })
      .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
    for (const [minId, key] of withMinId) {
      slugs.set(key, `${base}-${minId}`);
    }
  }
  return slugs;
}

module.exports = function () {
  const raw = fs.readFileSync(DATA_PATH, "utf-8");
  const all = JSON.parse(raw);

  // O(1) parent/reply lookups (post.njk resolves these per post) -- also
  // sidesteps relying on Jinja2-only filters like selectattr/first that
  // Nunjucks doesn't actually provide, by doing the lookup here in JS
  // instead of scanning `all` from within a template.
  const byId = new Map();
  for (const post of all) byId.set(post.id, post);

  // -- Author already carries a slug from the Python ETL (dd.md §7.3) --
  const byAuthorSlug = new Map();
  for (const post of all) {
    const slug = post.author.slug;
    if (!byAuthorSlug.has(slug)) {
      byAuthorSlug.set(slug, {
        slug,
        displayName: post.author.display_name,
        posts: [],
      });
    }
    byAuthorSlug.get(slug).posts.push(post);
  }
  const authors = Array.from(byAuthorSlug.values()).sort(
    (a, b) => b.posts.length - a.posts.length
  );

  // -- Topic slugs are computed here (not precomputed by the ETL) --
  const postsBySubject = new Map();
  for (const post of all) {
    const key = post.subject_normalized;
    if (!postsBySubject.has(key)) postsBySubject.set(key, []);
    postsBySubject.get(key).push(post);
  }
  const topicSlugs = resolveSlugs(postsBySubject);
  const byTopicSlug = new Map();
  for (const [normalizedSubject, posts] of postsBySubject) {
    const slug = topicSlugs.get(normalizedSubject);
    // Display subject is the *opening* post's real subject (posts is
    // chronologically ascending, mirroring `all` -- see threadsList below),
    // not the grouping key itself: subject_normalized is lowercased and has
    // "Re:"/list-name prefixes stripped for matching purposes only, and was
    // never meant to be shown to a reader.
    byTopicSlug.set(slug, { slug, subject: posts[0].subject, posts });
  }
  const topics = Array.from(byTopicSlug.values()).sort(
    (a, b) => b.posts.length - a.posts.length
  );

  // -- Browse by year/month, from date_utc ("YYYY-MM-DD...") --
  const byYear = new Map();
  for (const post of all) {
    const year = post.date_utc.slice(0, 4);
    const month = post.date_utc.slice(5, 7);
    if (!byYear.has(year)) byYear.set(year, { year, posts: [], byMonth: new Map() });
    const yearEntry = byYear.get(year);
    yearEntry.posts.push(post);
    if (!yearEntry.byMonth.has(month)) yearEntry.byMonth.set(month, { month, posts: [] });
    yearEntry.byMonth.get(month).posts.push(post);
  }
  const years = Array.from(byYear.keys()).sort().reverse();

  // Sorted (Jan..Dec) month array per year, for browse-year.njk's listing --
  // a Map's insertion order follows first-occurrence-in-`all` order, which
  // isn't necessarily calendar order. Also a flat, pagination-friendly list
  // of every (year, month) combo across the whole archive, for
  // browse-month.njk (Eleventy's `pagination.data` needs an array it can
  // walk, same reason `threadsList` exists below for threads).
  const monthsList = [];
  for (const yearEntry of byYear.values()) {
    yearEntry.monthsList = Array.from(yearEntry.byMonth.values()).sort((a, b) =>
      a.month < b.month ? -1 : a.month > b.month ? 1 : 0
    );
    for (const monthEntry of yearEntry.monthsList) {
      monthsList.push({ year: yearEntry.year, month: monthEntry.month, posts: monthEntry.posts });
    }
  }

  // -- Threads, ordered chronologically within each --
  const byThreadId = new Map();
  for (const post of all) {
    if (!byThreadId.has(post.thread_id)) byThreadId.set(post.thread_id, []);
    byThreadId.get(post.thread_id).push(post);
  }
  for (const posts of byThreadId.values()) {
    posts.sort((a, b) => (a.date_utc < b.date_utc ? -1 : a.date_utc > b.date_utc ? 1 : 0));
  }
  // Array form (not just the Map above) so thread.njk can paginate over it
  // directly -- Eleventy's `pagination.data` expects an array/object it can
  // walk by dot-path, not a Map.
  const threadsList = Array.from(byThreadId.entries()).map(([id, posts]) => ({
    id,
    posts,
  }));

  // `all` is stored ascending by date_utc (etl.py sorts it that way before
  // writing data/posts.json); Home's "recent posts" wants the reverse.
  const recentPosts = all.slice(-10).reverse();

  return {
    all,
    byId,
    recentPosts,
    byAuthorSlug,
    authors,
    byTopicSlug,
    topics,
    byYear,
    years,
    monthsList,
    byThreadId,
    threadsList,
  };
};

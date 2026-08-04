// See post.11tydata.js for why these are JS functions rather than
// Nunjucks template strings in front matter: shared-array reuse across
// pagination items, and double-escaping of quotes/ampersands in subjects.
module.exports = {
  eleventyComputed: {
    title: (data) => `Thread: ${data.posts.byId.get(data.thread.id).subject}`,
    description: (data) =>
      `${data.posts.byId.get(data.thread.id).subject} — a ${data.thread.posts.length}-post thread from the Traveller_TNE archive.`,
    breadcrumb: (data) => [
      { label: "Home", url: "/" },
      { label: `${data.posts.byId.get(data.thread.id).subject} (thread)` },
    ],
  },
};

// See post.11tydata.js -- eleventyComputed values that are Nunjucks
// template strings in front matter YAML share mutable state across
// pagination items and double-render (double-escape) plain strings; JS
// functions here avoid both.
module.exports = {
  eleventyComputed: {
    title: (data) => data.author.displayName,
    description: (data) =>
      `${data.author.posts.length} post${data.author.posts.length !== 1 ? "s" : ""} by ${data.author.displayName} in the Traveller_TNE archive.`,
    breadcrumb: (data) => [
      { label: "Home", url: "/" },
      { label: "Authors", url: "/authors/" },
      { label: data.author.displayName },
    ],
  },
};

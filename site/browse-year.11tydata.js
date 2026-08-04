// See post.11tydata.js -- eleventyComputed values that are Nunjucks
// template strings in front matter YAML share mutable state across
// pagination items and double-render (double-escape) plain strings; JS
// functions here avoid both.
module.exports = {
  eleventyComputed: {
    title: (data) => `${data.year}`,
    description: (data) =>
      `Posts from ${data.year} in the Traveller_TNE archive, by month.`,
    breadcrumb: (data) => [
      { label: "Home", url: "/" },
      { label: "Browse", url: "/browse/" },
      { label: `${data.year}` },
    ],
  },
};

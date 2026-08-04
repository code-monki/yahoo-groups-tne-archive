// See post.11tydata.js -- eleventyComputed values that are Nunjucks
// template strings in front matter YAML share mutable state across
// pagination items and double-render (double-escape) plain strings; JS
// functions here avoid both.
module.exports = {
  eleventyComputed: {
    title: (data) => data.topic.subject,
    description: (data) =>
      `${data.topic.posts.length} post${data.topic.posts.length !== 1 ? "s" : ""} on "${data.topic.subject}" in the Traveller_TNE archive.`,
    breadcrumb: (data) => [
      { label: "Home", url: "/" },
      { label: "Topics", url: "/topics/" },
      { label: data.topic.subject },
    ],
  },
};

// See post.11tydata.js -- eleventyComputed values that are Nunjucks
// template strings in front matter YAML share mutable state across
// pagination items and double-render (double-escape) plain strings; JS
// functions here avoid both.
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

module.exports = {
  eleventyComputed: {
    title: (data) =>
      `${MONTH_NAMES[parseInt(data.monthData.month, 10) - 1]} ${data.monthData.year}`,
    description: (data) =>
      `Posts from ${MONTH_NAMES[parseInt(data.monthData.month, 10) - 1]} ${data.monthData.year} in the Traveller_TNE archive.`,
    breadcrumb: (data) => [
      { label: "Home", url: "/" },
      { label: "Browse", url: "/browse/" },
      { label: `${data.monthData.year}`, url: `/browse/${data.monthData.year}/` },
      { label: `${MONTH_NAMES[parseInt(data.monthData.month, 10) - 1]} ${data.monthData.year}` },
    ],
  },
};

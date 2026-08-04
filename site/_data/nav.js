// Single source of truth for global nav (FR-16) -- rendered twice (mobile
// disclosure + desktop inline list) by the same macro in base.njk so both
// stay in sync automatically.
module.exports = [
  { label: "Home", url: "/" },
  { label: "Browse", url: "/browse/" },
  { label: "Authors", url: "/authors/" },
  { label: "Topics", url: "/topics/" },
  { label: "Files", url: "/files/" },
  { label: "Search", url: "/search/" },
  { label: "Help", url: "/help/" },
];

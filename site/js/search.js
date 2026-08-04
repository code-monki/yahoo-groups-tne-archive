// ADR-0011/ADR-0015: custom UI against Pagefind's JS API, loaded only on
// this page. Imported via its full pathPrefix-aware URL (set by search.njk
// as window.PAGEFIND_BASE) so Pagefind's own import.meta.url-based asset
// resolution -- and its derived result URLs -- land under the right
// GitHub Pages subpath automatically, with no manual basePath/baseUrl
// override needed.
(async () => {
  const form = document.getElementById("search-form");
  const input = document.getElementById("search-input");
  const status = document.getElementById("results-status");
  const list = document.getElementById("results-list");
  const loadMoreBtn = document.getElementById("load-more");

  // Pagefind's search() returns lightweight refs for every match; .data()
  // fetches that page's own index fragment, one network request each. A
  // common query (e.g. "orbit") can still match hundreds of posts in this
  // archive -- fetching/rendering all of them up front is wasted work and
  // an unusably long page, so results (already relevance- and subject-
  // weight-sorted by Pagefind) are paged in batches via "Load more".
  const PAGE_SIZE = 40;

  // Search-in-progress state, driving the "Load more" handler below.
  let currentQuery = "";
  let currentRefs = [];
  let shownCount = 0;

  function appendResults(results) {
    for (const result of results) {
      const li = document.createElement("li");
      li.className = "result-item";

      const link = document.createElement("a");
      link.className = "post-title";
      link.href = result.url;
      link.textContent = result.meta.title || result.url;
      li.appendChild(link);

      const meta = document.createElement("span");
      meta.className = "post-meta";
      meta.textContent = [result.meta.author, result.meta.date].filter(Boolean).join(" · ");
      li.appendChild(meta);

      const snippet = document.createElement("p");
      snippet.className = "result-snippet";
      // Pagefind-generated excerpt HTML, <mark>-wrapped around matched
      // terms (FR-13) -- trusted output from our own build step, not
      // user-supplied.
      snippet.innerHTML = result.excerpt;
      li.appendChild(snippet);

      list.appendChild(li);
    }
  }

  function updateStatus() {
    const total = currentRefs.length;
    status.textContent =
      shownCount < total
        ? `Showing ${shownCount} of ${total} results for “${currentQuery}”.`
        : `${total} result${total === 1 ? "" : "s"} for “${currentQuery}”.`;
    loadMoreBtn.hidden = shownCount >= total;
  }

  async function loadNextPage() {
    const nextRefs = currentRefs.slice(shownCount, shownCount + PAGE_SIZE);
    const results = await Promise.all(nextRefs.map((r) => r.data()));
    appendResults(results);
    shownCount += nextRefs.length;
    updateStatus();
  }

  async function runSearch(pagefind, query) {
    list.innerHTML = "";
    shownCount = 0;
    currentQuery = query;
    currentRefs = [];
    if (!query) {
      status.textContent = "";
      loadMoreBtn.hidden = true;
      return;
    }
    status.textContent = "Searching…";
    const search = await pagefind.search(query);
    // Deliberately not score-filtering here: Pagefind's fuzzy/edit-distance
    // matching means even a nonsense query returns *something*, but a
    // genuine single-occurrence stemmed match (FR-10 requires these to
    // surface) can score just as low as pure noise -- confirmed against
    // the real index, a real "orbiting"-only match scored 4.13, barely
    // above a garbage query's 3.98 ceiling. No score threshold reliably
    // separates the two without risking FR-10 matches disappearing, so
    // this shows whatever Pagefind returns rather than second-guessing it.
    currentRefs = search.results;
    if (currentRefs.length === 0) {
      status.textContent = `No results for “${query}”.`;
      loadMoreBtn.hidden = true;
      return;
    }
    await loadNextPage();
  }

  const params = new URLSearchParams(window.location.search);
  const initialQuery = params.get("q") || "";
  if (initialQuery) input.value = initialQuery;

  status.textContent = "Loading search index…";
  const pagefind = await import(window.PAGEFIND_BASE + "pagefind.js");
  await pagefind.init();
  status.textContent = "";

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = input.value.trim();
    const url = new URL(window.location.href);
    if (query) url.searchParams.set("q", query);
    else url.searchParams.delete("q");
    window.history.replaceState({}, "", url);
    runSearch(pagefind, query);
  });

  loadMoreBtn.addEventListener("click", () => loadNextPage());

  if (initialQuery) runSearch(pagefind, initialQuery);
})();

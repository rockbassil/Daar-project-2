const $ = (selector) => document.querySelector(selector);
const fmt = (n) => Number(n).toLocaleString();
let page = 1;
let activeSearch = null;
let requestNumber = 0;
let controller = null;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function sourceLink(book, className) {
  const link = element('a', className);
  // Only use known Gutenberg record links; never inject stored HTML or URLs.
  link.href = `https://www.gutenberg.org/ebooks/${Number(book.id)}`;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  return link;
}

function bookCard(book, index) {
  const card = element('article', 'book-card');
  const top = element('div', 'card-top');
  const cover = element('div', 'mini-cover', book.title);
  cover.setAttribute('aria-hidden', 'true');
  const info = element('div');
  info.append(element('div', 'book-number', `NO. ${String(index).padStart(2, '0')}`));
  info.append(element('h3', '', book.title));
  info.append(element('p', 'author', book.author));
  top.append(cover, info);
  const stats = element('div', 'card-stats');
  stats.append(element('span', '', `${fmt(book.occurrences)} occurrences`));
  stats.append(element('span', '', `PageRank ${book.pagerank.toFixed(5)}`));
  const link = sourceLink(book, 'book-link');
  link.append(element('span', '', 'Open book on Gutenberg'), element('span', '', '↗'));
  card.append(top, stats, link);
  return card;
}

async function loadStats() {
  try {
    const response = await fetch('/api/stats');
    if (!response.ok) throw new Error('Could not connect to the library.');
    const data = await response.json();
    $('#collection-strip').replaceChildren(...[
      `${fmt(data.books)} books to explore`, `${fmt(data.words)} words within`,
      `${fmt(data.terms)} distinct words`, data.graph ? 'Connected by shared vocabulary' : 'Connections not built yet'
    ].map((text) => element('span', '', text)));
    const notes = [];
    if (!data.corpus_ready) notes.push(`Development collection: ${fmt(data.books)} books. The assignment requires at least 1,664 books of 10,000+ words each.`);
    if (!data.graph) notes.push('PageRank and recommendations will be available after the graph is built.');
    $('#notice').hidden = !notes.length;
    $('#notice').textContent = notes.join(' ');
  } catch (error) {
    $('#collection-strip').textContent = error.message;
  }
}

function updateMode() {
  const regex = $('input[name="mode"]:checked').value === 'regex';
  $('#regex-help').hidden = !regex;
  $('#query').placeholder = regex ? 'Try sea|ocean or adventur.*' : 'Try ocean, adventure, or mystery…';
  $('#search-hint').textContent = regex ? 'Find indexed words that match a regular expression.' : 'One word is all it takes. We search inside every indexed book.';
}

async function runSearch(newSearch = true) {
  if (newSearch) {
    const query = $('#query').value.trim();
    if (!query) { $('#query').focus(); return; }
    activeSearch = { q: query, mode: $('input[name="mode"]:checked').value, ranking: $('#ranking').value };
    page = 1;
  }
  if (!activeSearch) return;
  const number = ++requestNumber;
  if (controller) controller.abort();
  controller = new AbortController();
  $('#results').setAttribute('aria-busy', 'true');
  $('#status').className = '';
  $('#status').textContent = 'Following your word through the library…';
  $('#results').replaceChildren();
  $('#recommendations-section').hidden = true;
  $('#matched-terms').hidden = true;
  $('#pagination').hidden = true;
  $('#result-meta').textContent = '';
  try {
    const response = await fetch(`/api/search?${new URLSearchParams({ ...activeSearch, page })}`, { signal: controller.signal });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Search failed. Please try again.');
    if (number !== requestNumber) return;
    $('#results-heading').textContent = `Books connected to “${data.query}”`;
    $('#result-meta').textContent = `${fmt(data.total)} results · ${fmt(data.elapsed_ms)} ms`;
    $('#status').textContent = data.total ? '' : 'No books found. Try another word or a broader expression.';
    if (!data.graph_ready && data.total) $('#status').textContent = 'Graph not built yet: results use occurrence counts until PageRank is available.';
    $('#results').replaceChildren(...data.results.map((book, i) => bookCard(book, (page - 1) * data.page_size + i + 1)));
    if (data.mode === 'regex') {
      $('#matched-terms').hidden = false;
      $('#matched-terms').textContent = `Matched ${fmt(data.matched_term_count)} indexed words: ${data.matched_terms.join(', ')}${data.matched_term_count > 30 ? ', …' : ''}`;
    }
    const pages = Math.ceil(data.total / data.page_size);
    $('#pagination').hidden = pages <= 1;
    $('#page-label').textContent = `Page ${page} of ${pages}`;
    $('#previous').disabled = page <= 1;
    $('#next').disabled = page >= pages;
    $('#recommendations-section').hidden = !data.recommendations.length;
    $('#recommendations').replaceChildren(...data.recommendations.map((book) => {
      const link = sourceLink(book, 'recommendation');
      link.append(element('h3', '', book.title), element('p', '', book.author),
        element('p', '', `${(book.similarity * 100).toFixed(1)}% vocabulary overlap with a top result ↗`));
      return link;
    }));
    history.replaceState(null, '', `/?${new URLSearchParams(activeSearch)}`);
  } catch (error) {
    if (error.name === 'AbortError' || number !== requestNumber) return;
    $('#status').className = 'error';
    $('#status').textContent = error.message;
  } finally {
    if (number === requestNumber) $('#results').setAttribute('aria-busy', 'false');
  }
}

$('#search-form').addEventListener('submit', (event) => { event.preventDefault(); runSearch(); });
document.querySelectorAll('input[name="mode"]').forEach((input) => input.addEventListener('change', updateMode));
document.querySelectorAll('[data-query]').forEach((button) => button.addEventListener('click', () => {
  $('#query').value = button.dataset.query;
  $('input[value="keyword"]').checked = true;
  updateMode();
  runSearch();
}));
$('#ranking').addEventListener('change', () => { if (activeSearch) runSearch(); });
$('#previous').addEventListener('click', () => { if (page > 1) { page--; runSearch(false); } });
$('#next').addEventListener('click', () => { page++; runSearch(false); });
const initial = new URLSearchParams(location.search);
if (initial.has('q')) {
  $('#query').value = initial.get('q').slice(0, 128);
  if (initial.get('mode') === 'regex') $('input[value="regex"]').checked = true;
  if (initial.get('ranking') === 'frequency') $('#ranking').value = 'frequency';
  updateMode();
  runSearch();
}
loadStats();

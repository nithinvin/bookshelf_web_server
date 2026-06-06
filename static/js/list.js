/* list.js — live search, filter, sort for the book list page */

(function () {
  var searchInput  = document.getElementById('searchInput');
  var searchClear  = document.getElementById('searchClear');
  var ratingFilter = document.getElementById('ratingFilter');
  var sortSelect   = document.getElementById('sortSelect');
  var grid         = document.getElementById('bookGrid');
  var emptyState   = document.getElementById('emptyState');

  if (!grid) return; // no books at all — static empty state shown by server

  function getCards() {
    return Array.from(grid.querySelectorAll('.book-card'));
  }

  function applyFilters() {
    var query     = searchInput.value.trim().toLowerCase();
    var minRating = parseFloat(ratingFilter.value) || 0;
    var sortKey   = sortSelect.value;

    // Show / hide clear button
    searchClear.hidden = query.length === 0;

    var cards = getCards();
    var visible = [];

    cards.forEach(function (card) {
      var title  = card.dataset.title  || '';
      var author = card.dataset.author || '';
      var rating = parseFloat(card.dataset.rating) || 0;

      var matchesQuery  = !query || title.includes(query) || author.includes(query);
      var matchesRating = rating >= minRating;

      if (matchesQuery && matchesRating) {
        card.classList.remove('hidden');
        visible.push(card);
      } else {
        card.classList.add('hidden');
      }
    });

    // Sort visible cards
    visible.sort(function (a, b) {
      if (sortKey === 'title')  return a.dataset.title.localeCompare(b.dataset.title);
      if (sortKey === 'author') return a.dataset.author.localeCompare(b.dataset.author);
      if (sortKey === 'year')   return parseInt(b.dataset.year)   - parseInt(a.dataset.year);
      if (sortKey === 'rating') return parseFloat(b.dataset.rating) - parseFloat(a.dataset.rating);
      return 0;
    });

    // Re-append in sorted order (hidden ones stay where they are, invisible)
    visible.forEach(function (card) { grid.appendChild(card); });

    // Toggle empty state
    if (emptyState) {
      emptyState.hidden = visible.length > 0;
    }
  }

  // Debounce helper — avoids firing on every keystroke
  function debounce(fn, ms) {
    var timer;
    return function () {
      clearTimeout(timer);
      timer = setTimeout(fn, ms);
    };
  }

  searchInput.addEventListener('input',  debounce(applyFilters, 180));
  ratingFilter.addEventListener('change', applyFilters);
  sortSelect.addEventListener('change',   applyFilters);

  searchClear.addEventListener('click', function () {
    searchInput.value = '';
    searchClear.hidden = true;
    applyFilters();
    searchInput.focus();
  });

  // Expose for inline onclick in template
  window.clearSearch = function () {
    searchInput.value = '';
    ratingFilter.value = '0';
    sortSelect.value = 'title';
    applyFilters();
  };

  // Run once on load to apply default sort
  applyFilters();
}());

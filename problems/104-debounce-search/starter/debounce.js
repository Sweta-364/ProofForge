// BROKEN: the previous timer is never cancelled, so every keystroke fires.
function debounce(fn, delay) {
  return function (...args) {
    setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

function runSearch(event) {
  fetch(`/api/search?q=${encodeURIComponent(event.target.value)}`)
    .then((res) => res.json())
    .then(renderResults);
}

const searchInput = document.getElementById('search');
searchInput.addEventListener('input', debounce(runSearch, 300));

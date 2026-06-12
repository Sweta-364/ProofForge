function debounce(fn, delay) {
  let timerId = null;
  return function (...args) {
    clearTimeout(timerId);
    timerId = setTimeout(() => {
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

// BROKEN: comment author/text are injected as raw HTML - stored XSS.
const list = document.getElementById('comment-list');

function renderComment(comment) {
  const item = document.createElement('li');
  item.className = 'comment';
  item.innerHTML = `<strong>${comment.author}</strong>: ${comment.text}`;
  list.appendChild(item);
}

function renderAll(comments) {
  list.innerHTML = '';
  comments.forEach(renderComment);
}

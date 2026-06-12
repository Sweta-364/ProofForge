const list = document.getElementById('comment-list');

function renderComment(comment) {
  const item = document.createElement('li');
  item.className = 'comment';
  const author = document.createElement('strong');
  author.textContent = comment.author;
  item.appendChild(author);
  item.appendChild(document.createTextNode(': ' + comment.text));
  list.appendChild(item);
}

function renderAll(comments) {
  list.innerHTML = '';
  comments.forEach(renderComment);
}

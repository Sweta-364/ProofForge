// BROKEN: no error handling - a failed request leaves the page blank.
const userList = document.getElementById('user-list');
const errorBox = document.getElementById('error-box');

function showError(message) {
  errorBox.textContent = message;
  errorBox.style.display = 'block';
}

function renderUsers(users) {
  userList.innerHTML = '';
  for (const user of users) {
    const item = document.createElement('li');
    item.textContent = user.username;
    userList.appendChild(item);
  }
}

async function loadUsers() {
  const response = await fetch('/api/users');
  const users = await response.json();
  renderUsers(users);
}

loadUsers();

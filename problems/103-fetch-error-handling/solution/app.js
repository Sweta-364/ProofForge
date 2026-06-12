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
  try {
    const response = await fetch('/api/users');
    if (!response.ok) {
      showError(`Could not load users (HTTP ${response.status}).`);
      return;
    }
    const users = await response.json();
    renderUsers(users);
  } catch (error) {
    showError('Network error - please check your connection and try again.');
  }
}

loadUsers();

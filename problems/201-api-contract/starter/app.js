// Frontend consumer of the contract - read-only context for this issue.
async function loadProfile(userId) {
  const res = await fetch(`/api/profile/${userId}`);
  if (!res.ok) {
    showNotFound();
    return;
  }
  const profile = await res.json();
  document.getElementById('username').textContent = profile.username;
  document.getElementById('email').textContent = profile.email;
  document.getElementById('joined').textContent = `Joined ${profile.joined}`;
  document.getElementById('id-badge').textContent = `#${profile.id}`;
}

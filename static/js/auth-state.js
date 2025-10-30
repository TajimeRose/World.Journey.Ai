(() => {
  const firebaseCtx = window.__FIREBASE__;
  if (!firebaseCtx || !firebaseCtx.auth || !firebaseCtx.authApi || !firebaseCtx.dbApi) {
    console.warn('Firebase not initialised; auth UI disabled.');
    return;
  }

  const { auth, authApi, dbApi } = firebaseCtx;
  const { onAuthStateChanged, signOut } = authApi;
  const { ref, get } = dbApi;

  const DEFAULT_USER_NAME = 'ผู้ใช้งาน';
  const GUEST_NAME = 'ผู้เยี่ยมชม';

  const body = document.body || document.createElement('body');
  const requiresAuth = body.classList.contains('requires-auth');
  const loginPage = body.classList.contains('login-body');

  const userControls = document.getElementById('userControls');
  const guestControls = document.getElementById('guestControls');
  const userNameNode = document.getElementById('userDisplayName');
  const userEmailNode = document.getElementById('userEmail');
  const userAvatar = document.getElementById('userAvatar');
  const logoutButton = document.getElementById('logoutButton');

  function broadcastAuthChange(displayName, email, { guest } = { guest: false }) {
    const fallback = guest ? GUEST_NAME : DEFAULT_USER_NAME;
    const safeName = displayName && displayName.trim() ? displayName.trim() : fallback;
    window.__USER_DISPLAY_NAME__ = safeName;
    window.__USER_EMAIL__ = email || '';
    window.dispatchEvent(
      new CustomEvent('wj-auth-changed', {
        detail: { displayName: safeName, email: email || '' },
      }),
    );
  }

  function showGuestView() {
    if (guestControls) guestControls.hidden = false;
    if (userControls) {
      userControls.hidden = true;
      userControls.classList.remove('is-visible');
    }
    if (userNameNode) userNameNode.textContent = GUEST_NAME;
    if (userEmailNode) userEmailNode.textContent = '';
    updateAvatar(GUEST_NAME);
    broadcastAuthChange(GUEST_NAME, '', { guest: true });
  }

  function showUserView() {
    if (guestControls) guestControls.hidden = true;
    if (userControls) {
      userControls.hidden = false;
      window.requestAnimationFrame(() => {
        userControls.classList.add('is-visible');
      });
    }
  }

  async function resolveDisplayName(user) {
    if (!user) return '';
    if (user.displayName) return user.displayName;
    try {
      const snapshot = await get(ref(`/users/${user.uid}/name`));
      const value = snapshot.val();
      if (typeof value === 'string' && value.trim()) {
        return value.trim();
      }
    } catch (error) {
      console.warn('Failed to fetch display name', error);
    }
    if (user.email) {
      return user.email.split('@')[0];
    }
    return DEFAULT_USER_NAME;
  }

  function updateAvatar(name) {
    if (!userAvatar) return;
    const initial = (name || DEFAULT_USER_NAME).trim().charAt(0).toUpperCase();
    userAvatar.textContent = initial || 'A';
  }

  async function populateUser(user) {
    const displayName = await resolveDisplayName(user);
    if (userNameNode) {
      userNameNode.textContent = displayName || DEFAULT_USER_NAME;
    }
    if (userEmailNode) {
      userEmailNode.textContent = user?.email || '';
    }
    updateAvatar(displayName);
    showUserView();
    broadcastAuthChange(displayName, user?.email || '');
  }

  if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
      try {
        await signOut(auth);
        showGuestView();
      } catch (error) {
        console.error('Sign out failed', error);
      }
    });
  }

  onAuthStateChanged(auth, async (user) => {
    if (!user) {
      showGuestView();
      if (requiresAuth) {
        window.location.replace('/login');
      }
      return;
    }

    await populateUser(user);

    if (loginPage) {
      window.location.replace('/');
    }
  });
})();

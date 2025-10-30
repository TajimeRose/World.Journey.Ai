(() => {
  const firebaseCtx = window.__FIREBASE__;
  if (!firebaseCtx || !firebaseCtx.auth || !firebaseCtx.authApi || !firebaseCtx.dbApi) {
    console.error('Firebase is not configured; login disabled.');
    return;
  }

  const { auth, authApi, dbApi } = firebaseCtx;
  const { signInWithEmailAndPassword, createUserWithEmailAndPassword, updateProfile } = authApi;
  const { ref, update } = dbApi;

  const form = document.getElementById('auth-form');
  const modeButtons = document.querySelectorAll('[data-auth-mode]');
  const submitButton = document.getElementById('submitButton');
  const submitLabel = submitButton?.querySelector('.submit-text');
  const generalError = document.getElementById('form-error');

  let currentMode = 'login';

  function setFieldVisibility(wrapper, visible) {
    if (!wrapper) return;
    wrapper.classList.toggle('is-hidden', !visible);
    const inputs = wrapper.querySelectorAll('input');
    inputs.forEach((input) => {
      if (visible) {
        input.removeAttribute('disabled');
        if (wrapper.dataset.authRequired === 'true') {
          input.setAttribute('required', 'true');
        }
      } else {
        input.setAttribute('disabled', 'true');
        input.removeAttribute('required');
        input.value = '';
      }
    });
  }

  function clearErrors() {
    if (generalError) generalError.textContent = '';
    form?.querySelectorAll('.form-error[data-error-for]').forEach((node) => {
      node.textContent = '';
    });
  }

  function setFieldError(fieldId, message) {
    if (!form) return;
    const selector = `.form-error[data-error-for="${fieldId}"]`;
    const node = form.querySelector(selector);
    if (node) {
      node.textContent = message || '';
    }
  }

  const ERROR_MESSAGES = {
    'auth/invalid-email': 'เธญเธตเน€เธกเธฅเนเธกเนเธ–เธนเธเธ•เนเธญเธ',
    'auth/user-not-found': 'เนเธกเนเธเธเธเธฑเธเธเธตเธเธตเน เธเธฃเธธเธ“เธฒเธ•เธฃเธงเธเธชเธญเธเธญเธตเธเธเธฃเธฑเนเธ',
    'auth/wrong-password': 'เธฃเธซเธฑเธชเธเนเธฒเธเนเธกเนเธ–เธนเธเธ•เนเธญเธ',
    'auth/missing-password': 'เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธฃเธซเธฑเธชเธเนเธฒเธ',
    'auth/email-already-in-use': 'เธญเธตเน€เธกเธฅเธเธตเนเธ–เธนเธเนเธเนเธเธฒเธเนเธฅเนเธง',
    'auth/weak-password': 'เธฃเธซเธฑเธชเธเนเธฒเธเธ•เนเธญเธเธกเธตเธเธงเธฒเธกเธขเธฒเธงเธญเธขเนเธฒเธเธเนเธญเธข 6 เธ•เธฑเธงเธญเธฑเธเธฉเธฃ',
    'auth/network-request-failed': 'เน€เธเธทเนเธญเธกเธ•เนเธญเน€เธเธฃเธทเธญเธเนเธฒเธขเนเธกเนเธชเธณเน€เธฃเนเธ',
    'auth/too-many-requests': 'เธเธขเธฒเธขเธฒเธกเธซเธฅเธฒเธขเธเธฃเธฑเนเธเน€เธเธดเธเนเธ เธเธฃเธธเธ“เธฒเธฅเธญเธเนเธซเธกเนเธ เธฒเธขเธซเธฅเธฑเธ',
  };

  function mapError(error) {
    return ERROR_MESSAGES[error?.code] || 'เน€เธเธดเธ”เธเนเธญเธเธดเธ”เธเธฅเธฒเธ” เธเธฃเธธเธ“เธฒเธฅเธญเธเนเธซเธกเนเธญเธตเธเธเธฃเธฑเนเธ';
  }

  async function saveDisplayName(user, name) {
    if (!user || !name) return;
    const cleanName = name.trim();
    try {
      await updateProfile(user, { displayName: cleanName });
    } catch (error) {
      console.warn('เธเธฑเธเธ—เธถเธเธเธทเนเธญเนเธ Firebase เนเธกเนเธชเธณเน€เธฃเนเธ', error);
    }
    try {
      const userRef = ref(`/users/${user.uid}`);
      await update(userRef, {
        name: cleanName,
        email: user.email || '',
        updatedAt: Date.now(),
      });
    } catch (error) {
      console.warn('เธเธฑเธเธ—เธถเธเธเนเธญเธกเธนเธฅเธเธนเนเนเธเนเนเธกเนเธชเธณเน€เธฃเนเธ', error);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form || !submitButton) return;

    clearErrors();

    const formData = new FormData(form);
    const email = (formData.get('email') || '').toString().trim();
    const password = (formData.get('password') || '').toString();

    if (!email) {
      setFieldError('email', 'เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธญเธตเน€เธกเธฅ');
      return;
    }

    if (!password) {
      setFieldError('password', 'เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธฃเธซเธฑเธชเธเนเธฒเธ');
      return;
    }

    let displayName = '';
    if (currentMode === 'signup') {
      displayName = (formData.get('displayName') || '').toString().trim();
      const confirmPassword = (formData.get('confirmPassword') || '').toString();

      if (!displayName) {
        setFieldError('displayName', 'เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธเธทเนเธญเธ—เธตเนเธ•เนเธญเธเธเธฒเธฃเนเธชเธ”เธ');
        return;
      }

      if (password !== confirmPassword) {
        setFieldError('confirmPassword', 'เธฃเธซเธฑเธชเธเนเธฒเธเธ•เนเธญเธเธ•เธฃเธเธเธฑเธ');
        return;
      }
    }

    submitButton.disabled = true;
    submitButton.setAttribute('aria-busy', 'true');

    try {
      if (currentMode === 'login') {
        await signInWithEmailAndPassword(auth, email, password);
      } else {
        const credential = await createUserWithEmailAndPassword(auth, email, password);
        await saveDisplayName(credential.user, displayName);
      }
      if (currentMode === 'signup') {
        window.location.replace('/index.html');
      } else {
        window.location.replace('/');
      }
    } catch (error) {
      const message = mapError(error);
      if (generalError) {
        generalError.textContent = message;
      }
    } finally {
      submitButton.disabled = false;
      submitButton.removeAttribute('aria-busy');
    }
  }

  function updateMode(mode) {
    currentMode = mode;
    modeButtons.forEach((button) => {
      const buttonMode = button.getAttribute('data-auth-mode');
      const isActive = buttonMode === mode;
      button.classList.toggle('is-active', isActive);
      button.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    if (submitLabel) {
      submitLabel.textContent =
        mode === 'login' ? submitLabel.dataset.labelLogin : submitLabel.dataset.labelSignup;
    }

    const signupFields = form?.querySelectorAll('[data-auth-required]') || [];
    signupFields.forEach((field) => setFieldVisibility(field, mode === 'signup'));

    clearErrors();
  }

  modeButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const mode = button.getAttribute('data-auth-mode') || 'login';
      updateMode(mode);
    });
  });

  form?.addEventListener('submit', handleSubmit);
  updateMode(currentMode);
})();


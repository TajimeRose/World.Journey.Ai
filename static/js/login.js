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
    'auth/invalid-email': 'อีเมลไม่ถูกต้อง',
    'auth/user-not-found': 'ไม่พบบัญชีนี้ กรุณาตรวจสอบอีกครั้ง',
    'auth/wrong-password': 'รหัสผ่านไม่ถูกต้อง',
    'auth/missing-password': 'กรุณากรอกรหัสผ่าน',
    'auth/email-already-in-use': 'อีเมลนี้ถูกใช้งานแล้ว',
    'auth/weak-password': 'รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร',
    'auth/network-request-failed': 'เชื่อมต่อเครือข่ายไม่สำเร็จ',
    'auth/too-many-requests': 'พยายามหลายครั้งเกินไป กรุณาลองใหม่ภายหลัง',
  };

  function mapError(error) {
    return ERROR_MESSAGES[error?.code] || 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง';
  }

  async function saveDisplayName(user, name) {
    if (!user || !name) return;
    const cleanName = name.trim();
    try {
      await updateProfile(user, { displayName: cleanName });
    } catch (error) {
      console.warn('บันทึกชื่อใน Firebase ไม่สำเร็จ', error);
    }
    try {
      const userRef = ref(`/users/${user.uid}`);
      await update(userRef, {
        name: cleanName,
        email: user.email || '',
        updatedAt: Date.now(),
      });
    } catch (error) {
      console.warn('บันทึกข้อมูลผู้ใช้ไม่สำเร็จ', error);
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
      setFieldError('email', 'กรุณากรอกอีเมล');
      return;
    }

    if (!password) {
      setFieldError('password', 'กรุณากรอกรหัสผ่าน');
      return;
    }

    let displayName = '';
    if (currentMode === 'signup') {
      displayName = (formData.get('displayName') || '').toString().trim();
      const confirmPassword = (formData.get('confirmPassword') || '').toString();

      if (!displayName) {
        setFieldError('displayName', 'กรุณากรอกชื่อที่ต้องการแสดง');
        return;
      }

      if (password !== confirmPassword) {
        setFieldError('confirmPassword', 'รหัสผ่านต้องตรงกัน');
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
      window.location.replace('/');
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

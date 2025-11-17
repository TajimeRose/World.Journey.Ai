(() => {
  const firebaseCtx = window.__FIREBASE__;
  const AUTH_ENABLED = !!(firebaseCtx && firebaseCtx.auth && firebaseCtx.authApi && firebaseCtx.dbApi);

  if (!AUTH_ENABLED) {
    console.warn('Firebase is not configured; UI enabled but submission disabled.');
  }

  const auth = AUTH_ENABLED ? firebaseCtx.auth : null;
  const signInWithEmailAndPassword = AUTH_ENABLED ? firebaseCtx.authApi.signInWithEmailAndPassword : null;
  const createUserWithEmailAndPassword = AUTH_ENABLED ? firebaseCtx.authApi.createUserWithEmailAndPassword : null;
  const updateProfile = AUTH_ENABLED ? firebaseCtx.authApi.updateProfile : async () => { };
  const ref = AUTH_ENABLED ? firebaseCtx.dbApi.ref : () => { };
  const update = AUTH_ENABLED ? firebaseCtx.dbApi.update : async () => { };

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
    if (generalError) {
      generalError.textContent = '';
      generalError.classList.remove('success');
    }
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
    'auth/invalid-email': 'รูปแบบอีเมลไม่ถูกต้อง',
    'auth/user-not-found': 'ไม่พบบัญชีผู้ใช้ กรุณาตรวจสอบอีเมลหรือสมัครสมาชิก',
    'auth/wrong-password': 'รหัสผ่านไม่ถูกต้อง',
    'auth/missing-password': 'กรุณากรอกรหัสผ่าน',
    'auth/email-already-in-use': 'อีเมลนี้ถูกใช้งานแล้ว กรุณาเข้าสู่ระบบหรือใช้อีเมลอื่น',
    'auth/weak-password': 'รหัสผ่านอ่อนเกินไป ต้องมีอย่างน้อย 6 ตัวอักษร',
    'auth/network-request-failed': 'ไม่สามารถเชื่อมต่อเครือข่ายได้ กรุณาตรวจสอบอินเทอร์เน็ต',
    'auth/too-many-requests': 'พยายามเข้าสู่ระบบมากเกินไป กรุณารอสักครู่แล้วลองใหม่',
    'auth/user-disabled': 'บัญชีนี้ถูกระงับการใช้งาน',
    'auth/operation-not-allowed': 'ระบบไม่อนุญาตให้ทำรายการนี้',
    'auth/invalid-credential': 'ข้อมูลเข้าสู่ระบบไม่ถูกต้อง กรุณาตรวจสอบอีเมลและรหัสผ่าน',
  };

  function mapError(error) {
    console.error('Auth error:', error);
    return ERROR_MESSAGES[error?.code] || `เกิดข้อผิดพลาด: ${error?.message || 'กรุณาลองใหม่'}`;
  }

  async function saveDisplayName(user, name) {
    if (!user || !name) return;
    const cleanName = name.trim();
    try {
      await updateProfile(user, { displayName: cleanName });
    } catch (error) {
      console.warn('บันทึกชื่อไปยัง Firebase ไม่สำเร็จ', error);
    }
    try {
      const userRef = ref(`/users/${user.uid}`);
      await update(userRef, {
        name: cleanName,
        email: user.email || '',
        updatedAt: Date.now(),
      });
    } catch (error) {
      console.warn('บันทึกข้อมูลผู้ใช้ลง Firebase ไม่สำเร็จ', error);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form || !submitButton) return;

    clearErrors();

    // Check if Firebase is available
    if (!AUTH_ENABLED) {
      if (generalError) {
        generalError.textContent = 'ระบบเข้าสู่ระบบยังไม่พร้อมใช้งาน กรุณารีเฟรชหน้าเว็บ';
        generalError.classList.remove('success');
      }
      return;
    }

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
        setFieldError('confirmPassword', 'รหัสผ่านไม่ตรงกัน');
        return;
      }
    }

    submitButton.disabled = true;
    submitButton.setAttribute('aria-busy', 'true');

    try {
      if (currentMode === 'login') {
        await signInWithEmailAndPassword(auth, email, password);
        // Redirect to index page after successful login
        window.location.replace('/');
      } else {
        const credential = await createUserWithEmailAndPassword(auth, email, password);
        await saveDisplayName(credential.user, displayName);

        // Show success message for registration
        if (generalError) {
          generalError.classList.add('success');
          generalError.textContent = 'สมัครสมาชิกสำเร็จ! กำลังนำคุณไปหน้าแรก...';
        }

        // Update submit button text
        if (submitLabel) {
          submitLabel.textContent = 'กำลังเข้าสู่ระบบ...';
        }

        // Small delay to show success message, then redirect to index page
        setTimeout(() => {
          window.location.replace('/');
        }, 1500);

        // Don't re-enable the button since we're redirecting
        return;
      }
    } catch (error) {
      const message = mapError(error);
      if (generalError) {
        generalError.textContent = message;
        generalError.classList.remove('success');
      }
    } finally {
      // Only re-enable button if we're not redirecting
      if (currentMode !== 'signup' || !generalError?.classList.contains('success')) {
        submitButton.disabled = false;
        submitButton.removeAttribute('aria-busy');
      }
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


(() => {
  'use strict';

  // Configuration and constants
  const REDIRECT_DELAY = 1500;
  const ERROR_MESSAGES = {
    'auth/invalid-email': 'อีเมลไม่ถูกต้อง',
    'auth/user-not-found': 'ไม่พบบัญชีนี้ กรุณาตรวจสอบอีกครั้ง',
    'auth/wrong-password': 'รหัสผ่านไม่ถูกต้อง',
    'auth/missing-password': 'กรุณากรอกรหัสผ่าน',
    'auth/email-already-in-use': 'อีเมลนี้ถูกใช้งานแล้ว',
    'auth/weak-password': 'รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร',
    'auth/network-request-failed': 'เชื่อมต่อเครือข่ายไม่สำเร็จ',
    'auth/too-many-requests': 'พยายามหลายครั้งเกินไป กรุณาลองใหม่ภายหลัง',
    'auth/invalid-credential': 'ข้อมูลการเข้าสู่ระบบไม่ถูกต้อง',
    'auth/user-disabled': 'บัญชีนี้ถูกปิดใช้งาน',
  };

  // Firebase initialization check
  const firebaseCtx = window.__FIREBASE__;
  if (!firebaseCtx?.auth || !firebaseCtx?.authApi || !firebaseCtx?.dbApi) {
    console.error('Firebase is not configured; login disabled.');
    return;
  }

  const { auth, authApi, dbApi } = firebaseCtx;
  const { signInWithEmailAndPassword, createUserWithEmailAndPassword, updateProfile } = authApi;
  const { ref, update } = dbApi;

  // DOM elements
  const elements = {
    form: document.getElementById('auth-form'),
    modeButtons: document.querySelectorAll('[data-auth-mode]'),
    submitButton: document.getElementById('submitButton'),
    submitLabel: document.querySelector('#submitButton .submit-text'),
    generalError: document.getElementById('form-error'),
  };

  // State
  let currentMode = 'login';
  let isProcessing = false;

  // Utility functions
  function validateElements() {
    const required = ['form', 'submitButton', 'generalError'];
    return required.every(key => elements[key] !== null);
  }

  function mapError(error) {
    return ERROR_MESSAGES[error?.code] || 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง';
  }

  function sanitizeInput(input) {
    return typeof input === 'string' ? input.trim() : '';
  }

  // UI Management functions
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
    if (elements.generalError) {
      elements.generalError.textContent = '';
      elements.generalError.classList.remove('success');
    }
    
    elements.form?.querySelectorAll('.form-error[data-error-for]').forEach((node) => {
      node.textContent = '';
    });
  }

  function setFieldError(fieldId, message) {
    if (!elements.form || !message) return;
    
    const errorNode = elements.form.querySelector(`.form-error[data-error-for="${fieldId}"]`);
    if (errorNode) {
      errorNode.textContent = message;
    }
  }

  function setGeneralError(message, isSuccess = false) {
    if (!elements.generalError) return;
    
    elements.generalError.textContent = message;
    elements.generalError.classList.toggle('success', isSuccess);
  }

  function setSubmitButtonState(disabled, text = null) {
    if (!elements.submitButton) return;
    
    elements.submitButton.disabled = disabled;
    elements.submitButton.setAttribute('aria-busy', disabled ? 'true' : 'false');
    
    if (text && elements.submitLabel) {
      elements.submitLabel.textContent = text;
    }
  }

  function resetSubmitButtonText() {
    if (!elements.submitLabel) return;
    
    const key = currentMode === 'login' ? 'labelLogin' : 'labelSignup';
    elements.submitLabel.textContent = elements.submitLabel.dataset[key] || 'ส่ง';
  }

  // Validation functions
  function validateEmail(email) {
    return email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function validatePassword(password) {
    return password && password.length >= 6;
  }

  function validateFormData(formData) {
    const errors = {};
    
    const email = sanitizeInput(formData.get('email'));
    const password = formData.get('password')?.toString() || '';
    
    if (!email) {
      errors.email = 'กรุณากรอกอีเมล';
    } else if (!validateEmail(email)) {
      errors.email = 'รูปแบบอีเมลไม่ถูกต้อง';
    }
    
    if (!password) {
      errors.password = 'กรุณากรอกรหัสผ่าน';
    } else if (currentMode === 'signup' && !validatePassword(password)) {
      errors.password = 'รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร';
    }
    
    if (currentMode === 'signup') {
      const displayName = sanitizeInput(formData.get('displayName'));
      const confirmPassword = formData.get('confirmPassword')?.toString() || '';
      
      if (!displayName) {
        errors.displayName = 'กรุณากรอกชื่อที่ต้องการแสดง';
      }
      
      if (password !== confirmPassword) {
        errors.confirmPassword = 'รหัสผ่านต้องตรงกัน';
      }
    }
    
    return {
      isValid: Object.keys(errors).length === 0,
      errors,
      data: {
        email,
        password,
        displayName: currentMode === 'signup' ? sanitizeInput(formData.get('displayName')) : '',
      }
    };
  }

  // Firebase operations
  async function saveDisplayName(user, name) {
    if (!user || !name) return;
    
    const cleanName = sanitizeInput(name);
    if (!cleanName) return;
    
    const operations = [];
    
    // Update Firebase Auth profile
    operations.push(
      updateProfile(user, { displayName: cleanName })
        .catch(error => console.warn('Failed to update Firebase Auth profile:', error))
    );
    
    // Update Realtime Database
    operations.push(
      update(ref(`/users/${user.uid}`), {
        name: cleanName,
        email: user.email || '',
        updatedAt: Date.now(),
      }).catch(error => console.warn('Failed to update user data in database:', error))
    );
    
    await Promise.allSettled(operations);
  }

  async function performAuthentication(data) {
    if (currentMode === 'login') {
      await signInWithEmailAndPassword(auth, data.email, data.password);
      window.location.replace('/');
    } else {
      const credential = await createUserWithEmailAndPassword(auth, data.email, data.password);
      await saveDisplayName(credential.user, data.displayName);
      
      // Show success message and redirect
      setGeneralError('สมัครสมาชิกสำเร็จ! กำลังนำคุณไปหน้าแรก...', true);
      setSubmitButtonState(true, 'กำลังเข้าสู่ระบบ...');
      
      setTimeout(() => {
        window.location.replace('/');
      }, REDIRECT_DELAY);
    }
  }

  // Event handlers
  async function handleSubmit(event) {
    event.preventDefault();
    
    if (!elements.form || !elements.submitButton || isProcessing) return;
    
    clearErrors();
    
    const formData = new FormData(elements.form);
    const validation = validateFormData(formData);
    
    if (!validation.isValid) {
      Object.entries(validation.errors).forEach(([field, message]) => {
        setFieldError(field, message);
      });
      return;
    }
    
    isProcessing = true;
    setSubmitButtonState(true);
    
    try {
      await performAuthentication(validation.data);
    } catch (error) {
      console.error('Authentication error:', error);
      setGeneralError(mapError(error));
      resetSubmitButtonText();
    } finally {
      // Only re-enable if not redirecting
      if (currentMode === 'login' || !elements.generalError?.classList.contains('success')) {
        isProcessing = false;
        setSubmitButtonState(false);
        resetSubmitButtonText();
      }
    }
  }

  function handleModeChange(mode) {
    if (isProcessing || mode === currentMode) return;
    
    currentMode = mode;
    clearErrors();
    
    // Update mode buttons
    elements.modeButtons.forEach((button) => {
      const buttonMode = button.getAttribute('data-auth-mode');
      const isActive = buttonMode === mode;
      button.classList.toggle('is-active', isActive);
      button.setAttribute('aria-selected', isActive.toString());
    });
    
    // Update submit button text
    resetSubmitButtonText();
    
    // Toggle signup-specific fields
    const signupFields = elements.form?.querySelectorAll('[data-auth-required]') || [];
    signupFields.forEach((field) => setFieldVisibility(field, mode === 'signup'));
  }

  // Initialization
  function init() {
    if (!validateElements()) {
      console.error('Required DOM elements not found');
      return;
    }
    
    // Set initial mode
    handleModeChange(currentMode);
    
    // Add event listeners
    elements.modeButtons.forEach((button) => {
      button.addEventListener('click', (event) => {
        event.preventDefault();
        const mode = button.getAttribute('data-auth-mode') || 'login';
        handleModeChange(mode);
      });
    });
    
    if (elements.form) {
      elements.form.addEventListener('submit', handleSubmit);
    }
    
    console.log('Login system initialized successfully');
  }

  // Start the application
  init();
})();

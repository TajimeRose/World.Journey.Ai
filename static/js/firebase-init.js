import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.4.0/firebase-app.js';
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  updateProfile,
} from 'https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js';
import {
  getDatabase,
  ref as dbRef,
  get as dbGet,
  update as dbUpdate,
  set as dbSet,
  push as dbPush,
  onValue as dbOnValue,
} from 'https://www.gstatic.com/firebasejs/12.4.0/firebase-database.js';

(function initialiseFirebase() {
  const config = window.FIREBASE_CONFIG;
  if (!config) {
    console.warn('Firebase config not provided - authentication disabled.');
    return;
  }

  let app;
  try {
    app = initializeApp(config);
  } catch (error) {
    console.error('Failed to initialise Firebase app', error);
    return;
  }

  const auth = getAuth(app);
  const database = getDatabase(app);

  window.__FIREBASE__ = {
    app,
    auth,
    database,
    authApi: {
      onAuthStateChanged,
      signInWithEmailAndPassword,
      createUserWithEmailAndPassword,
      signOut,
      updateProfile,
    },
    dbApi: {
      ref: (path) => dbRef(database, path),
      get: dbGet,
      update: dbUpdate,
      set: dbSet,
      push: async (pathOrRef, value) => {
        // pathOrRef can be a string path or a ref
        const r = typeof pathOrRef === 'string' ? dbRef(database, pathOrRef) : pathOrRef;
        const newRef = await dbPush(r);
        if (value !== undefined) {
          await dbSet(newRef, value);
        }
        return newRef;
      },
      onValue: (pathOrRef, cb) => {
        const r = typeof pathOrRef === 'string' ? dbRef(database, pathOrRef) : pathOrRef;
        return dbOnValue(r, cb);
      },
    },
    helpers: {
      /**
       * Save a simple message into the `messages` node.
       * Returns the pushed Ref.
       */
      saveMessage: async (user, text) => {
        const time = new Date().toISOString();
        try {
          const newRef = await dbPush(dbRef(database, 'messages'));
          await dbSet(newRef, { user, text, time });
          return newRef;
        } catch (err) {
          console.warn('Failed to save message to Firebase', err);
          throw err;
        }
      },
    },
  };
  window.__USER_DISPLAY_NAME__ = window.__USER_DISPLAY_NAME__ || 'ผู้ใช้งาน';
})();

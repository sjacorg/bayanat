const SESSION_CADENCE_MAX_MS = 120000;
const SESSION_CADENCE_MIN_MS = 15000;
const SESSION_WARNING_WINDOW_MAX_MS = 60000;
const SESSION_COUNTDOWN_TICK_MS = 1000;
const SESSION_KEEPALIVE_LOCK_TTL_MS = 10000;
const SESSION_REFRESH_STORAGE_KEY = 'bayanat:last-session-refresh';
const SESSION_KEEPALIVE_LOCK_STORAGE_KEY = 'bayanat:session-keepalive-lock';

const sessionLifecycleMixin = {
  data: () => ({
    sessionWarningVisible: false,
    sessionWarningRemainingSeconds: 0,
    sessionStaySignedInLoading: false,
    sessionLifecycleIntervalId: null,
    sessionCountdownIntervalId: null,
    sessionInteractedSinceRefresh: false,
    sessionLastInteractionAt: 0,
    sessionExpiryReported: false,
    sessionTabId: `${Date.now()}-${Math.random()}`,
  }),
  computed: {
    sessionLifetimeMs() {
      return Number(window.__SESSION_LIFETIME__ || 0) * 1000;
    },
    sessionRefreshCadenceMs() {
      if (!this.sessionLifetimeMs) return 0;
      return Math.min(
        SESSION_CADENCE_MAX_MS,
        Math.max(SESSION_CADENCE_MIN_MS, Math.floor(this.sessionLifetimeMs / 3))
      );
    },
    sessionWarningWindowMs() {
      if (!this.sessionLifetimeMs) return 0;
      return Math.min(SESSION_WARNING_WINDOW_MAX_MS, this.sessionLifetimeMs);
    },
    sessionAuthPending() {
      return Boolean(this.isSignInDialogVisible || this.isReauthDialogVisible || this.isSignInDialogLoading);
    },
  },
  mounted() {
    if (!window.__username__ || !this.sessionLifetimeMs) return;

    this.recordSessionRefresh();
    this.addSessionActivityListeners();
    document.addEventListener('session-refreshed', this.recordSessionRefresh);
    document.addEventListener('authentication-required', this.pauseSessionLifecycle);
    document.addEventListener('visibilitychange', this.handleSessionVisibilityChange);

    this.sessionLifecycleIntervalId = setInterval(
      this.checkSessionLifecycle,
      Math.min(SESSION_CADENCE_MIN_MS, this.sessionRefreshCadenceMs)
    );
    this.sessionCountdownIntervalId = setInterval(this.updateSessionWarning, SESSION_COUNTDOWN_TICK_MS);
  },
  beforeUnmount() {
    this.removeSessionActivityListeners();
    document.removeEventListener('session-refreshed', this.recordSessionRefresh);
    document.removeEventListener('authentication-required', this.pauseSessionLifecycle);
    document.removeEventListener('visibilitychange', this.handleSessionVisibilityChange);
    clearInterval(this.sessionLifecycleIntervalId);
    clearInterval(this.sessionCountdownIntervalId);
  },
  methods: {
    addSessionActivityListeners() {
      ['input', 'keydown', 'pointerdown', 'wheel', 'touchmove'].forEach(eventName => {
        window.addEventListener(eventName, this.markSessionInteraction, { passive: true });
      });
    },
    removeSessionActivityListeners() {
      ['input', 'keydown', 'pointerdown', 'wheel', 'touchmove'].forEach(eventName => {
        window.removeEventListener(eventName, this.markSessionInteraction);
      });
    },
    markSessionInteraction() {
      if (this.sessionAuthPending || this.sessionWarningVisible) return;
      this.sessionInteractedSinceRefresh = true;
      this.sessionLastInteractionAt = Date.now();
    },
    pauseSessionLifecycle() {
      this.sessionWarningVisible = false;
      this.sessionInteractedSinceRefresh = false;
      this.sessionExpiryReported = false;
    },
    handleSessionVisibilityChange() {
      if (document.visibilityState !== 'visible') {
        this.sessionWarningVisible = false;
        return;
      }

      this.updateSessionWarning();
      this.checkSessionLifecycle();
    },
    recordSessionRefresh() {
      this.setSessionStorageValue(SESSION_REFRESH_STORAGE_KEY, String(Date.now()));
      this.sessionInteractedSinceRefresh = false;
      this.sessionWarningVisible = false;
      this.sessionExpiryReported = false;
    },
    lastSessionRefreshAt() {
      return Number(this.getSessionStorageValue(SESSION_REFRESH_STORAGE_KEY) || Date.now());
    },
    sessionKeepaliveLocked() {
      const now = Date.now();
      const lock = this.getSessionStorageValue(SESSION_KEEPALIVE_LOCK_STORAGE_KEY) || '';
      const lockedUntil = Number(lock.split(':')[0] || 0);
      if (lockedUntil > now) return true;

      const nextLock = `${now + SESSION_KEEPALIVE_LOCK_TTL_MS}:${this.sessionTabId}`;
      this.setSessionStorageValue(SESSION_KEEPALIVE_LOCK_STORAGE_KEY, nextLock);
      return this.getSessionStorageValue(SESSION_KEEPALIVE_LOCK_STORAGE_KEY) !== nextLock;
    },
    releaseSessionKeepaliveLock() {
      const lock = this.getSessionStorageValue(SESSION_KEEPALIVE_LOCK_STORAGE_KEY) || '';
      if (!lock.endsWith(`:${this.sessionTabId}`)) return;
      this.removeSessionStorageValue(SESSION_KEEPALIVE_LOCK_STORAGE_KEY);
    },
    getSessionStorageValue(key) {
      try {
        return localStorage.getItem(key);
      } catch (error) {
        return null;
      }
    },
    setSessionStorageValue(key, value) {
      try {
        localStorage.setItem(key, value);
      } catch (error) {
        return null;
      }
    },
    removeSessionStorageValue(key) {
      try {
        localStorage.removeItem(key);
      } catch (error) {
        return null;
      }
    },
    async checkSessionLifecycle() {
      if (document.visibilityState !== 'visible') return;

      if (this.sessionAuthPending) {
        this.pauseSessionLifecycle();
        return;
      }

      this.updateSessionWarning();
      if (this.sessionWarningVisible) return;

      const elapsed = Date.now() - this.lastSessionRefreshAt();
      if (!this.sessionInteractedSinceRefresh) return;
      if (this.sessionLastInteractionAt <= this.lastSessionRefreshAt()) {
        this.sessionInteractedSinceRefresh = false;
        return;
      }

      if (elapsed < this.sessionRefreshCadenceMs) return;

      if (this.sessionKeepaliveLocked()) return;

      try {
        await axios.get('/admin/api/session-check');
      } catch (error) {
        // Any failure (401, network, timeout) is a no-op here; a real
        // expiry is surfaced separately via the global 401 interceptor.
      } finally {
        this.releaseSessionKeepaliveLock();
      }
    },
    updateSessionWarning() {
      if (this.sessionAuthPending || document.visibilityState !== 'visible') {
        this.sessionWarningVisible = false;
        return;
      }

      const remainingMs = this.sessionLifetimeMs - (Date.now() - this.lastSessionRefreshAt());
      this.sessionWarningRemainingSeconds = Math.max(0, Math.ceil(remainingMs / 1000));

      if (remainingMs <= 0) {
        // A session found expired here - whether the countdown was showing,
        // the tab just woke from sleep, or it was backgrounded the whole
        // time - must hand off to the sign-in dialog itself. Otherwise the
        // page looks fine with a session that's actually already dead
        // underneath it until some unrelated request happens to 401.
        this.sessionWarningVisible = false;
        if (!this.sessionExpiryReported) {
          this.sessionExpiryReported = true;
          document.dispatchEvent(new CustomEvent('authentication-required'));
        }
        return;
      }

      this.sessionWarningVisible = remainingMs <= this.sessionWarningWindowMs;
    },
    async staySignedIn() {
      if (this.sessionStaySignedInLoading) return;

      try {
        this.sessionStaySignedInLoading = true;
        await axios.get('/admin/api/session-check');
      } catch (error) {
        // Any failure (401, network, timeout) is a no-op here; a real
        // expiry is surfaced separately via the global 401 interceptor.
      } finally {
        this.sessionStaySignedInLoading = false;
      }
    },
  },
};

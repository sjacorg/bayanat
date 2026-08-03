const sessionLifecycleMixin = {
  data: () => ({
    sessionWarningVisible: false,
    sessionWarningRemainingSeconds: 0,
    sessionStaySignedInLoading: false,
    sessionLifecycleIntervalId: null,
    sessionCountdownIntervalId: null,
    sessionInteractedSinceRefresh: false,
    sessionLastInteractionAt: 0,
    sessionTabId: `${Date.now()}-${Math.random()}`,
  }),
  computed: {
    sessionLifetimeMs() {
      return Number(window.__SESSION_LIFETIME__ || 0) * 1000;
    },
    sessionRefreshCadenceMs() {
      if (!this.sessionLifetimeMs) return 0;
      return Math.min(120000, Math.max(15000, Math.floor(this.sessionLifetimeMs / 3)));
    },
    sessionWarningWindowMs() {
      if (!this.sessionLifetimeMs) return 0;
      return Math.min(60000, this.sessionLifetimeMs);
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
      Math.min(15000, this.sessionRefreshCadenceMs)
    );
    this.sessionCountdownIntervalId = setInterval(this.updateSessionWarning, 1000);
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
      this.setSessionStorageValue('bayanat:last-session-refresh', String(Date.now()));
      this.sessionInteractedSinceRefresh = false;
      this.sessionWarningVisible = false;
    },
    lastSessionRefreshAt() {
      return Number(this.getSessionStorageValue('bayanat:last-session-refresh') || Date.now());
    },
    sessionKeepaliveLocked() {
      const now = Date.now();
      const lock = this.getSessionStorageValue('bayanat:session-keepalive-lock') || '';
      const lockedUntil = Number(lock.split(':')[0] || 0);
      if (lockedUntil > now) return true;

      const nextLock = `${now + 10000}:${this.sessionTabId}`;
      this.setSessionStorageValue('bayanat:session-keepalive-lock', nextLock);
      return this.getSessionStorageValue('bayanat:session-keepalive-lock') !== nextLock;
    },
    releaseSessionKeepaliveLock() {
      const lock = this.getSessionStorageValue('bayanat:session-keepalive-lock') || '';
      if (!lock.endsWith(`:${this.sessionTabId}`)) return;
      this.removeSessionStorageValue('bayanat:session-keepalive-lock');
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
        // 401s are handled by the global axios interceptor.
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
      this.sessionWarningVisible =
        remainingMs > 0 && remainingMs <= this.sessionWarningWindowMs;
    },
    async staySignedIn() {
      if (this.sessionStaySignedInLoading) return;

      try {
        this.sessionStaySignedInLoading = true;
        await axios.get('/admin/api/session-check');
      } catch (error) {
        // 401s are handled by the global axios interceptor.
      } finally {
        this.sessionStaySignedInLoading = false;
      }
    },
  },
};

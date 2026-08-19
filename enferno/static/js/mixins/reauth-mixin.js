const SESSION_RESTORED_STORAGE_KEY = 'bayanat:session-restored';

const reauthMixin = {
  data: () => ({
    isSignInDialogLoading: false,
    isReauthDialogVisible: false,
    isSignInDialogVisible: false,
    signInErrorMessage: null,
    signInForm: {
      username: window.__username__ || null,
      password: null,
      csrf_token: null,
    },
    twoFaSelectForm: null,
    verificationCode: null,
    signInStep: 'sign-in',
  }),
  created () {
    document.addEventListener('authentication-required', this.showLoginDialog);
    window.addEventListener('storage', this.onSessionRestoredElsewhere);
  },
  beforeUnmount() {
    document.removeEventListener('authentication-required', this.showLoginDialog);
    window.removeEventListener('storage', this.onSessionRestoredElsewhere);
  },
  methods: {
    onSessionRestoredElsewhere(event) {
      // Split-screen tabs never fire visibilitychange on each other, so a
      // sign-in in one tab needs an explicit cross-tab signal to close the
      // others' dialogs instead of waiting on a focus change that won't come.
      if (event.key !== SESSION_RESTORED_STORAGE_KEY || !event.newValue) return;
      if (!this.isSignInDialogVisible && !this.isReauthDialogVisible) return;

      // Same reasoning as onVisibilityChange: a sibling tab signing in only
      // proves *a* session exists, not that this tab's freshness reauth
      // requirement was satisfied.
      if (this.isReauthDialogVisible) return;

      // A different account signing in elsewhere is not this tab's session
      // coming back - completing here would replay this tab's pending
      // requests (e.g. an unsaved bulletin) under the other account's
      // cookie. Only self-close when the restored session matches who this
      // tab was signed in as.
      const [restoredUsername] = event.newValue.split('|');
      if (!this.isSameUsername(restoredUsername, window.__username__)) return;

      this.completeAuthentication();
    },
    async onVisibilityChange() {
      if (document.visibilityState !== 'visible') return; // only run when tab becomes active

      if (!this.isSignInDialogVisible && !this.isReauthDialogVisible) return;

      // A session-check only proves the session exists; it cannot prove a
      // freshness reauth requirement was satisfied. So it may auto-close the
      // plain sign-in dialog, but the freshness reauth dialog must still be
      // completed in this tab even if the underlying session is valid.
      if (this.isReauthDialogVisible) return;

      try {
        const response = await axios.get('/admin/api/session-check', { suppressGlobalErrorHandler: true });

        // The browser's cookie jar is shared across tabs: if a different
        // account signed in here since this tab loaded, session-check now
        // succeeds under that other account. That is not this tab's session
        // coming back, and completing here would replay this tab's pending
        // requests (e.g. an unsaved bulletin) under someone else's account.
        if (!this.isSameUsername(response?.data?.username, window.__username__)) return;

        this.completeAuthentication();
      } catch (error) {
        // Still expired - keep dialog open
      }
    },
    showLoginDialog(event) {
      if (this.isReauthRequired(event?.detail)) {
        this.isReauthDialogVisible = true;
      } else {
        this.isSignInDialogVisible = true;
      }

      // Start listening for tab focus
      document.addEventListener('visibilitychange', this.onVisibilityChange);
    },
    resetState() {
      // Stop listening when dialog closes
      document.removeEventListener('visibilitychange', this.onVisibilityChange);

      this.signInForm = {
        username: window.__username__ || null,
        password: null,
        csrf_token: null
      };
      this.isSignInDialogLoading = false;
      this.isSignInDialogVisible = false;
      this.isReauthDialogVisible = false;
      this.signInErrorMessage = null;
      this.twoFaSelectForm = null;
      this.verificationCode = null;
      this.signInStep = 'sign-in';
    },
    completeAuthentication() {
      this.resetState();
      drainSessionReplayQueue();
    },
    async signIn() {
      try {
        if (this.isSignInDialogLoading) return;
        this.isSignInDialogLoading = true;

        if (!this.signInForm.username || !this.signInForm.password) {
          return this.signInErrorMessage = "Username and password are required.";
        }

        // Fetch the CSRF token
        const csrfToken = await this.getCsrfToken();
        if (!csrfToken) return;
        this.signInForm.csrf_token = csrfToken;

        // Submit login request
        const signInResponse = await axios.post('/login', this.signInForm);

        // Handle success
        this.handleLoginResponse(signInResponse?.data?.response);
      } catch (err) {
        this.signInErrorMessage = handleRequestError(err);
      } finally {
        this.isSignInDialogLoading = false;
      }
    },
    async submitReauth() {
      try {
        if (this.isSignInDialogLoading) return;
        this.isSignInDialogLoading = true;

        if (!this.signInForm.password) {
          return this.signInErrorMessage = "Password is required.";
        }

        // Fetch the CSRF token
        const csrfToken = await this.getCsrfToken();
        if (!csrfToken) return;
        this.signInForm.csrf_token = csrfToken;

        // Submit login request
        await axios.post('/verify', {
          csrf_token: csrfToken,
          password: this.signInForm.password
        });

        // Handle success
        this.handleLoginResponse();
      } catch (err) {
        this.signInErrorMessage = handleRequestError(err);
      } finally {
        this.isSignInDialogLoading = false;
      }
    },
    async submitAuthenticatorCode() {
      try {
        if (this.isSignInDialogLoading) return;
        this.isSignInDialogLoading = true;

        if (!this.signInForm.csrf_token) {
          return this.signInErrorMessage = "Failed to retrieve CSRF token.";
        }

        // Submit login request
        await axios.post('/tf-validate', {
          csrf_token: this.signInForm.csrf_token,
          code: this.verificationCode
        });

        // Handle success
        this.handleLoginResponse();
      } catch (err) {
        this.signInErrorMessage = handleRequestError(err);
        if (err?.request?.status === 404) return this.goBackToSignIn();
      } finally {
        this.isSignInDialogLoading = false;
      }
    },
    async submitWebauthn() {
      try {
        if (this.isSignInDialogLoading) return;
        this.isSignInDialogLoading = true;

        if (!this.signInForm.csrf_token) {
          this.signInErrorMessage = "Failed to retrieve CSRF token.";
          return;
        }

        // Submit login request
        const wanResponse = await axios.post('/wan-signin', {
          csrf_token: this.signInForm.csrf_token,
        });
        const credentials = await this.getWebauthnCredentials(wanResponse.data?.response?.credential_options);
        await axios.post(`/wan-signin/${wanResponse.data?.response?.wan_state}`, {
          csrf_token: this.signInForm.csrf_token,
          credential: credentials,
          remember: wanResponse.data.response.remember
        });

        // Handle success
        this.handleLoginResponse();
      } catch (err) {
        this.signInErrorMessage = handleRequestError(err);
        if (err?.request?.status === 404) return this.goBackToSignIn();
      } finally {
        this.isSignInDialogLoading = false;
      }
    },
    handleLoginResponse(loginResponse) {
      if (loginResponse?.tf_required) {
        this.signInErrorMessage = null;
        if (loginResponse?.tf_select) return this.signInStep = '2fa-select'
        if (!loginResponse?.tf_setup_methods) {
          return this.signInStep = loginResponse?.tf_primary_method ?? loginResponse?.tf_method
        }

        return this.signInStep = loginResponse?.tf_setup_methods?.find(Boolean)
      }

      this.showSnack('Authentication successful');
      this.broadcastSessionRestored();
      this.completeAuthentication();
    },
    broadcastSessionRestored() {
      try {
        // Value must change on every write so sibling tabs' storage listeners
        // fire even if a previous signal was never cleared. Username is
        // included so sibling tabs can tell a same-account restore (safe to
        // auto-complete) apart from a different account signing in on this
        // browser (must not silently replay this tab's pending requests
        // under someone else's session).
        const username = this.signInForm.username || window.__username__ || '';
        localStorage.setItem(SESSION_RESTORED_STORAGE_KEY, `${Date.now()}|${username}`);
      } catch (error) {
        // Storage unavailable; other tabs simply won't self-close their dialog.
      }
    },
    async select2FAMethod() {
      try {
        if (this.isSignInDialogLoading) return;
        this.isSignInDialogLoading = true;

        if (!this.signInForm.csrf_token) {
          this.signInErrorMessage = "Failed to retrieve CSRF token.";
          return;
        }

        // Submit login request
        await axios.post('/tf-select', {
          csrf_token: this.signInForm.csrf_token,
          which: this.twoFaSelectForm
        });

        // Handle success
        this.signInStep = this.twoFaSelectForm;
      } catch (err) {
        this.signInErrorMessage = handleRequestError(err);
      } finally {
        this.isSignInDialogLoading = false;
      }
    },
    async getWebauthnCredentials(credentialOptions) {
      const options = {...credentialOptions};

      // Convert challenge and allowCredentials' IDs to Uint8Array
      options.challenge = Uint8Array.from(atob(options.challenge), c => c.charCodeAt(0));
      options.allowCredentials = options.allowCredentials.map(credential => ({
        ...credential,
        id: Uint8Array.from(atob(credential.id.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0)),
      }));

      // Call navigator.credentials.get() for WebAuthn authentication
      const credential = await navigator.credentials.get({ publicKey: options });
      
      // Convert credential response fields to base64 for server compatibility
      const credentialData = {
        id: credential.id,
        rawId: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
        type: credential.type,
        response: {
          clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(credential.response.clientDataJSON))),
          authenticatorData: btoa(String.fromCharCode(...new Uint8Array(credential.response.authenticatorData))),
          signature: btoa(String.fromCharCode(...new Uint8Array(credential.response.signature))),
          userHandle: credential.response.userHandle
          ? btoa(String.fromCharCode(...new Uint8Array(credential.response.userHandle)))
          : null,
        },
      };
      
      return credentialData
    },
    goBackToSignIn() {
      this.twoFaSelectForm = null;
      this.verificationCode = null;
      this.signInStep = 'sign-in';
    },
    async getCsrfToken() {
      const response = await axios.get('/csrf');
      const csrfToken = response?.data?.csrf_token;
      if (!csrfToken) this.signInErrorMessage = "Failed to retrieve CSRF token.";

      return csrfToken;
    },
    isReauthRequired(evt) {
      const reauthRequired = Boolean(evt?.response?.data?.response?.reauth_required);

      return reauthRequired;
    },
    isSameUsername(a, b) {
      // Login is case-insensitive server-side (SECURITY_USER_IDENTITY_ATTRIBUTES),
      // so "Alice" typed at sign-in and a stored "alice" are the same account.
      if (!a || !b) return false;
      return a.toLowerCase() === b.toLowerCase();
    }
  },
};

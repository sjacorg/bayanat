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
    callbackQueue: []
  }),
  created () {
    document.addEventListener('authentication-required', this.showLoginDialog);
  },
  beforeUnmount() {
    document.removeEventListener('authentication-required', this.showLoginDialog);
  },
  methods: {
    async onVisibilityChange() {
      if (document.visibilityState !== 'visible') return; // only run when tab becomes active

      // Only check if dialog is visible
      if (!(this.isSignInDialogVisible || this.isReauthDialogVisible)) return;
      
      try {
        await axios.get('/admin/api/session-check', { suppressGlobalErrorHandler: true });
        this.resetState(); // Session restored - close dialog
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

        // Run callbacks in queue
        await this.executeCallbackQueue();
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
      this.resetState();
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
    addToCallbackQueueIfReauthRequired(error, callbacks) {
      if (!this.isReauthRequired(error)) return;

      if (Array.isArray(callbacks)) {
          callbacks.forEach(callback => this.callbackQueue.push(callback));
      } else {
          this.callbackQueue.push(callbacks);
      }
    },
    async executeCallbackQueue() {
      for (const callback of this.callbackQueue) {
        await callback();
      }
      this.callbackQueue = [];
    },
    isReauthRequired(evt) {
      const reauthRequired = Boolean(evt?.response?.data?.response?.reauth_required);

      return reauthRequired;
    }
  },
};

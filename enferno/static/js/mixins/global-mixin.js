const UPDATE_POLL_INTERVAL = 60000; // Poll every minute for update indicator

const globalMixin = {
  mixins: [reauthMixin, notificationMixin],
  data: () => ({
    snackbar: false,
    snackMessage: '',

    // settings drawer
    settingsDrawer: false,
    settings: {},
    languages: languages,

    rules: {
      dateValidation(value) {
        // Check if the date is valid
        if (!value) {
          return true;
        }
        return dayjs(value).isValid() || 'Invalid date';
      },

      required: (value) => {
        if (Array.isArray(value)) return value.length > 0 || 'This field is required.';
        if (value && typeof value === 'object')
          return Object.keys(value).length > 0 || 'This field is required.';
        return !!value || 'This field is required.';
      },
    },
    dateFormats: {
      isoDate: 'YYYY-MM-DD',
      isoDatetime: 'YYYY-MM-DDTHH:mm',
      standardDate: 'DD/MM/YYYY',
      standardDatetime: 'DD/MM/YYYY h:mm A',
      standardTime: 'h:mm A',
      iso: 'iso',
      relative: 'relative',
      calendar: 'calendar',
      localeDate: 'L',
      localeDatetime: 'LLL'
    },
    dateOptions: {
      local: { local: true },
      utc: { utc: true },
      timezone: { timezone: 'UTC' },
      locale: { locale: 'en' }
    },
    updateInfo: null,
    checkingUpdates: false,
    updateError: null,
    updatePollIntervalId: null,
  }),
  created () {
    document.addEventListener('global-axios-error', this.showSnack);

    if (!window.__username__) return;

    api.get('/settings/load').then(res => {
      this.settings = res.data;
    });
  },
  mounted() {
    if (!window.__username__) return;
    if (!this.isAdminUser()) return;

    this.fetchUpdateInfo();
    this.startUpdatePolling();
    document.addEventListener('visibilitychange', this.handleUpdateVisibilityChangeForUpdates);
  },
  beforeUnmount() {
    document.removeEventListener('global-axios-error', this.showSnack);
    document.removeEventListener('visibilitychange', this.handleUpdateVisibilityChangeForUpdates);
    this.stopUpdatePolling();
  },
  methods: {
    /**
     * Format a date with Day.js supporting timezone, locale, and special formats.
     * @param {string|number|Date|dayjs.Dayjs} date - Date to format.
     * @param {string} format - Format string or keyword (e.g. 'iso', 'relative').
     * @param {Object} [options] - Optional: timezone, utc, locale.
     * @returns {string} Formatted date or empty string if invalid.
     */
    formatDate(date, format = this.dateFormats.standardDatetime, options = {}) {
      if (!date) return '';

      let d = dayjs(date);

      if (options.utc) {
        d = d.utc();
      } else if (options.local) {
          d = dayjs(date.includes('Z') ? date : date + 'Z');
          d = d.local();
      } else if (options.timezone) {
          d = d.tz(options.timezone);
      }

      if (options.locale) {
          d = d.locale(options.locale);
      }

      switch ((format || '').toLowerCase()) {
        case 'iso': return d.toISOString();
        case 'relative': return d.fromNow();
        case 'calendar': return d.calendar();
        default: return d.format(format);
      }
    },
    // Snack Bar
    showSnack(message) {
      if (typeof message === 'string') {
        this.snackMessage = message;
      } else {
        this.snackMessage = handleRequestError(message?.detail ?? message);
      }
      this.snackbar = true;
    },

        has_role(user, role) {
            for (const r of user.roles) {
                if (r.name === role) {
                    return true
                }
            }
            return false;
        },
        parseValidationError(response){
            if (response && response.errors){
                let message = '';
                for(const field in response.errors){
                    let fieldName = field;
                    if (fieldName.startsWith('item.')){
                        fieldName = fieldName.substring(5);
                    }
                    message += `<strong style="color:#b71c1c;">[${!fieldName.includes("__root__") ? fieldName : 'Validation Error'}]:</strong> ${response.errors[field]}<br/>`;
                }
                return message;
            }
            return response;
        },
        closeSnack(){
            this.snackbar = false;
            this.snackMessage = '';
        },

    saveSettings() {
        api.put('/settings/save', { settings: this.settings }).then(res => {
            this.$vuetify.theme.name = this.settings.dark ? 'dark' : 'light';
            this.showSnack('Settings have been saved!');
        }).catch(err => {
            this.showSnack(err.body);
        });
    },
    toggleUserSettingsDrawer() {
      // Toggle the settings drawer
      this.settingsDrawer = !this.settingsDrawer;

      // Close the notifications drawer if the settings drawer is open
      if (this.settingsDrawer) {
        this.notifications.ui.drawerVisible = false;
      }
    },
    updateLang(l) {
      this.settings.language = l
      this.saveSettings();
      setTimeout(() => {
          window.location.reload();
      }, 1000);
    },
    serverErrorPropsForField(serverErrors, key) {
      return {
        "error-messages": serverErrors?.[key],
        "onUpdate:modelValue": () => (serverErrors[key] = null),
      }
    },
    serverErrorPropsForDualField(
      serverErrors,
      originalKey,
      translationKey
    ) {
      return {
        "error-messages-original": serverErrors?.[originalKey],
        "onUpdate:original": () => (serverErrors[originalKey] = null),
        "error-messages-translation": serverErrors?.[translationKey],
        "onUpdate:translation": () => (serverErrors[translationKey] = null),
      }
    },
    isAdminUser() {
      return Boolean(window.__is_admin__);
    },
    startUpdatePolling() {
      if (this.updatePollIntervalId) return;
      this.updatePollIntervalId = setInterval(() => {
        this.fetchUpdateInfo();
      }, UPDATE_POLL_INTERVAL);
    },
    stopUpdatePolling() {
      if (!this.updatePollIntervalId) return;
      clearInterval(this.updatePollIntervalId);
      this.updatePollIntervalId = null;
    },
    handleUpdateVisibilityChangeForUpdates() {
      if (!this.isAdminUser()) return;
      if (document.visibilityState === 'visible') {
        this.fetchUpdateInfo();
        this.startUpdatePolling();
      } else {
        this.stopUpdatePolling();
      }
    },
    fetchUpdateInfo() {
      if (!this.isAdminUser()) {
        return Promise.resolve(null);
      }

      if (this._updateCheckInFlight) {
        return this._updateCheckInFlight;
      }

      this.checkingUpdates = true;
      this.updateError = null;

      this._updateCheckInFlight = axios
        .get('/admin/api/system/version/check', {
          params: { _ts: Date.now() },
          suppressGlobalErrorHandler: true,
        })
        .then((response) => {
          this.updateInfo = response.data;
          return response.data;
        })
        .catch((error) => {
          console.warn('Update check failed:', error);
          this.updateError = error;
          return null;
        })
        .finally(() => {
          this.checkingUpdates = false;
          this._updateCheckInFlight = null;
        });

      return this._updateCheckInFlight;
    },
    getUpdateIcon() {
      if (this.updateError) {
        return 'mdi-alert-circle-outline';
      }
      if (this.checkingUpdates) {
        return 'mdi-refresh';
      }
      if (this.updateInfo && this.updateInfo.update_available) {
        return 'mdi-download';
      }
      return 'mdi-check';
    },
    getUpdateIconClasses() {
      return {
        'mdi-spin': this.checkingUpdates,
      };
    },
  },
};

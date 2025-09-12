const globalMixin = {
  mixins: [reauthMixin, notificationMixin],
  components: {
    'ConfirmDialog': ConfirmDialog,
    'Toast': Toast,
  },
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
    }
  }),
  created () {
    document.addEventListener('global-axios-error', this.showSnack);

    if (!window.__username__) return;

    api.get('/settings/load').then(res => {
      this.settings = res.data;
    });
  },
  beforeUnmount() {
    document.removeEventListener('global-axios-error', this.showSnack);
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
    $confirm(options) {
      return this.$root.$refs.confirmDialog.show(options)
    },
    $toast(options) {
      return this.$root.$refs.toast.show(options)
    },
  },
};

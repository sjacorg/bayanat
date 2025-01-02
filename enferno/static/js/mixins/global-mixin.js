const globalMixin = {
  mixins: [reauthMixin],
  computed: {
    allowedDateFrom() {
      if (this.editedEvent?.to_date){
        // ensure date is not after the to_date
        return (current) => current <= dayjs(this.editedEvent.to_date).toDate();
      }
      return () => true;
    },
    allowedDateTo() {
      if (this.editedEvent?.from_date){
        // ensure date is not before the from_date
        return (current) => current >= dayjs(this.editedEvent.from_date).toDate();
      }
      return () => true;
    },
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
        return dayjs(value, 'YYYY-MM-DD', true).isValid() || 'Invalid date';
      },

      required: (value) => {
        if (Array.isArray(value)) return value.length > 0 || 'This field is required.';
        if (value && typeof value === 'object')
          return Object.keys(value).length > 0 || 'This field is required.';
        return !!value || 'This field is required.';
      },
      email: (value) => {
        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return pattern.test(value) || 'Invalid e-mail.';
      },
      password: (value) => {
        if (value.length < 8) {
          return 'Password must be at least 8 characters long.';
        }
        return true;
      },
      passwordMatch: (value, password) => {
        if (value !== password) {
          return 'Passwords do not match.';
        }
        return true;
      },
    },
  }),
  created () {
    document.addEventListener('global-axios-error', this.showSnack);

    if (!window.__username__) return;

    axios.get('/settings/load').then(res => {
      this.settings = res.data;
    });
  },
  beforeUnmount() {
    document.removeEventListener('global-axios-error', this.showSnack);
  },
  methods: {
    localDate: function (dt) {
      if (dt === null || dt === '') {
        return '';
      }
      // Z tells it's a UTC time
      const utcDate = new Date(`${dt}Z`);
      const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      return utcDate.toLocaleString('en-US', { timeZone: userTimezone });
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
        axios.put('/settings/save', { settings: this.settings }).then(res => {
            this.$vuetify.theme.name = this.settings.dark ? 'dark' : 'light';
            this.showSnack('Settings have been saved!');
        }).catch(err => {
            this.showSnack(err.body);
        });
    },

    updateLang(l) {
      this.settings.language = l
      this.saveSettings();
      setTimeout(() => {
        window.location.reload();
    }, 1000);
    },
  },
};

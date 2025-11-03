const Toast = Vue.defineComponent({
  data() {
    return {
      open: false,
      message: '',
      hideActions: false,
      iconProps: null,
      snackbarProps: {
        multiLine: true,
        variant: 'flat',
        rounded: 'lg',
        minHeight: 38,
      },
    };
  },
  methods: {
    show({
      message = '',
      hideActions = false,
      iconProps,
      snackbarProps = {},
    } = {}) {
      Object.assign(this, {
        message,
        hideActions,
        iconProps,
        snackbarProps: {
          multiLine: true,
          variant: 'flat',
          rounded: 'lg',
          minHeight: 38, ...snackbarProps
        },
        open: true,
      });
    },

    async close() {
      this.open = false;
      this.cleanup();
    },

    cleanup() {
      setTimeout(() => {
        this.message = '';
        this.hideActions = false;
        this.iconProps = null;
        this.snackbarProps = {
          multiLine: true,
          variant: 'flat',
          rounded: 'lg',
          minHeight: 38,
        };
      }, 300)
    },
  },
  template: `
    <v-snackbar v-model="open" multi-line v-bind="snackbarProps">
      <v-icon v-if="iconProps" class="mr-2" v-bind="iconProps"></v-icon>
      <span v-html="message"></span>
      <template v-if="!hideActions" #actions>
          <v-btn icon="mdi-close" variant="text" @click="close"></v-btn>
      </template>
    </v-snackbar>
  `,
});

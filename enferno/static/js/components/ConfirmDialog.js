const ConfirmDialog = Vue.defineComponent({
  data() {
    return {
      translations: window.translations,
      open: false,
      title: '',
      message: '',
      loading: false,
      dialogProps: {},

      cancelProps: { text: translations.cancel_, variant: 'outlined' },
      acceptProps: { text: translations.confirm_, color: 'primary', variant: 'flat' },

      onAccept: null,
      onReject: null,

      resolvePromise: null,
      rejectPromise: null,
    };
  },
  methods: {
    show({
      title = translations.confirmation_,
      message = translations.areYouSureYouWantToProceed_,
      cancelProps = {},
      acceptProps = {},
      dialogProps = {},
      onAccept = null,
      onReject = null,
    } = {}) {
      Object.assign(this, {
        title,
        message,
        dialogProps: { ...dialogProps },
        cancelProps: { text: translations.cancel_, variant: 'outlined', ...cancelProps },
        acceptProps: { text: translations.confirm_, color: 'primary', variant: 'flat', ...acceptProps },
        onAccept,
        onReject,
        loading: false,
        open: true,
      });

      return new Promise((resolve, rejectPromise) => {
        this.resolvePromise = resolve;
        this.rejectPromise = rejectPromise;
      });
    },

    async cancel() {
      await this.onReject?.();
      this.open = false;
      this.resolvePromise?.(false);
      this.cleanup();
    },

    async ok() {
      this.loading = true;
      
      try {
        await this.onAccept?.(); // if this throws, code below won't run
        this.open = false;
        this.resolvePromise?.(true);
        this.cleanup();
      } catch (error) {
        console.log('Something failed when confirming dialog', error)
      } finally {
        this.loading = false;
      }
    },

    cleanup() {
      setTimeout(() => {
        this.loading = false;
        this.onAccept = null;
        this.onReject = null;
        this.resolvePromise = null;
        this.rejectPromise = null;
        this.cancelProps = { text: translations.cancel_, variant: 'outlined' };
        this.acceptProps = { text: translations.confirm_, color: 'primary', variant: 'flat' };
        this.dialogProps = {};
      }, 300)
    },
  },
  template: `
    <v-dialog v-model="open" v-bind="{ persistent: loading, ...dialogProps}">
      <v-card rounded="12">
        <v-card-title class="px-7 pt-6 pb-0">
          <slot name="title">{{ title }}</slot>
        </v-card-title>

        <v-card-text class="px-7 pb-7 pt-2 text-pre-wrap">
          <slot>{{ message }}</slot>
        </v-card-text>

        <v-card-actions class="justify-end pb-7 px-7 pt-0">
          <slot name="actions">
            <v-btn
              :disabled="loading"
              @click="cancel"
              v-bind="cancelProps"
            >
              {{ cancelProps.text }}
            </v-btn>

            <v-btn
              :loading="loading"
              @click="ok"
              v-bind="acceptProps"
            >
              {{ acceptProps.text }}
            </v-btn>
          </slot>
        </v-card-actions>
      </v-card>
    </v-dialog>
  `,
});

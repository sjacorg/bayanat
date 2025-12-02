const ConfirmDialog = Vue.defineComponent({
  props: {
    disabledAccept: {
      type: Boolean,
      default: false,
    }
  },
  data() {
    return {
      translations: window.translations,
      data: null,
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
      data = null,
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
        data,
      });

      return new Promise((resolve, reject) => {
        this.resolvePromise = resolve;
        this.rejectPromise = reject;
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
      this.loading = false;
      this.onAccept = null;
      this.onReject = null;
      this.resolvePromise = null;
      this.rejectPromise = null;
      this.cancelProps = { text: translations.cancel_, variant: 'outlined' };
      this.acceptProps = { text: translations.confirm_, color: 'primary', variant: 'flat' };
      this.dialogProps = {};
      this.data = null;
    },
  },
  template: `
    <v-dialog v-model="open" v-bind="{ persistent: loading, ...dialogProps}" @after-leave="cleanup()">
      <v-card rounded="12">
        <v-card-title class="px-7 pt-6 pb-0">
          <slot name="title" :data="data">{{ title }}</slot>
        </v-card-title>

        <v-card-text class="px-7 pb-7 pt-2 text-pre-wrap">
          <slot :data="data">{{ message }}</slot>
        </v-card-text>

        <v-card-actions class="justify-end pb-7 px-7 pt-0">
          <slot name="actions" :data="data">
            <v-btn
              :disabled="loading"
              @click="cancel"
              v-bind="cancelProps"
            >
              {{ cancelProps.text }}
            </v-btn>

            <v-btn
              v-bind="acceptProps"
              :loading="loading"
              :disabled="disabledAccept || acceptProps.disabled"
              @click="ok"
            >
              {{ acceptProps.text }}
            </v-btn>
          </slot>
        </v-card-actions>
      </v-card>
    </v-dialog>
  `,
});

const ConfirmDialog = Vue.defineComponent({
  data() {
    return {
      open: false,
      title: '',
      message: '',
      resolve: null,
      reject: null,
      loading: false,
      color: null,
      cancelText: 'Cancel',
      confirmText: 'Confirm'
    }
  },
  methods: {
    show({ title = '', message = '' } = {}) {
      this.title = title
      this.message = message
      this.open = true
      this.loading = false

      return new Promise((resolve, reject) => {
        this.resolve = resolve
        this.reject = reject
      })
    },
    cancel() {
      this.open = false
      this.resolve(false)
    },
    ok() {
      this.loading = true
      setTimeout(() => {
        this.open = false
        this.resolve(true)
      }, 300)
    },
  },
  template: `
    <v-dialog v-model="open" max-width="250">
      <v-card rounded="12">
        <v-card-title class="text-h6">
          <slot name="title">{{ title }}</slot>
        </v-card-title>

        <v-card-text>
          <slot name="message">{{ message }}</slot>
        </v-card-text>

        <v-card-actions class="justify-end">
          <slot name="actions">
            <v-btn text :disabled="loading" @click="cancel">{{ cancelText }}</v-btn>
            <v-btn :color="color" :loading="loading" dark @click="ok">{{ confirmText }}</v-btn>
          </slot>
        </v-card-actions>
      </v-card>
    </v-dialog>
  `,
});

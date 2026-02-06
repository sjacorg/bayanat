const ErrorComponent = Vue.defineComponent({
  props: {
    error: {
      type: Error,
      required: true
    }
  },

  template: `
    <v-alert
      type="error"
      variant="tonal"
      density="compact"
      closable
      class="ma-2"
    >
      {{ error.message || window.translations.failedToLoadComponent_ }}
    </v-alert>
  `
});

window.ErrorComponent = ErrorComponent;
const DualField = Vue.defineComponent({
  name: 'DualField',
  props: {
    original: {
      type: String,
      default: '',
    },
    translation: {
      type: String,
      default: '',
    },
    errorMessagesOriginal: {
      type: [Array, String] ,
      default: () => [],
    },
    errorMessagesTranslation: {
      type: [Array, String],
      default: () => [],
    },
    rules: {
      type: Array,
      default: () => [],
    },
    rulesOriginal: {
      type: Array,
      default: () => [],
    },
    rulesTranslation: {
      type: Array,
      default: () => [],
    },
    labelOriginal: {
      type: String,
      default: 'Original',
    },
    labelTranslation: {
      type: String,
      default: 'Translation',
    },
    allowUnknown: {
      type: Boolean,
      default: false,
    },
    unknownTooltip: {
      type: String,
      default: "Unknown",
    },
  },
  emits: ['update:original', 'update:translation'],
  data() {
    return {
      isOriginalVisible: !(!this.original && this.translation),
      localOriginal: this.original,
      localTranslation: this.translation,
      hasAutoSelected: !!(this.original || this.translation),
    };
  },
  watch: {
    // Watch for prop changes and update local copies accordingly
    original(newVal) {
      this.localOriginal = newVal;
      this.autoSelectVisibleField();
    },
    translation(newVal) {
      this.localTranslation = newVal;
      this.autoSelectVisibleField();
    },
  },
  methods: {
    toggleField() {
      this.isOriginalVisible = !this.isOriginalVisible;
    },
    autoSelectVisibleField() {
      // Only runs once, the first time data arrives (e.g. async fetch after mount).
      // Skipped afterwards so it never overrides the user's manual toggle while editing.
      if (this.hasAutoSelected) return;
      if (!this.original && !this.translation) return;
      this.hasAutoSelected = true;
      this.isOriginalVisible = !(!this.original && this.translation);
    },
    setUnknown() {
      if (this.allowUnknown) {
        this.$emit('update:original', 'UNKNOWN');
        // Update local copy to reflect the change
        this.localOriginal = 'UNKNOWN';
      }
    }
  },
  template: `
    <v-sheet class="d-flex">
      <v-text-field
          v-if="isOriginalVisible"
          :label="labelOriginal"
          v-model="localOriginal"
          @update:modelValue="$emit('update:original', $event)"
          variant="outlined"
          append-inner-icon="mdi-web"
          @click:append-inner="toggleField"
          :rules="[...rulesOriginal, ...rules]"
          :error-messages="errorMessagesOriginal"
      >
        <template v-slot:append v-if="allowUnknown">
          <v-tooltip location="top" :text="unknownTooltip">
            <template v-slot:activator="{ props }">
              <v-btn icon="mdi-account-question" variant="plain" v-bind="props" @click="setUnknown">
              </v-btn>
            </template>
          </v-tooltip>
        </template>
      </v-text-field>

      <v-text-field
          v-else
          :label="labelTranslation"
          v-model="localTranslation"
          @update:modelValue="$emit('update:translation', $event)"
          variant="outlined"
          append-inner-icon="mdi-web"
          @click:append-inner="toggleField"
          :rules="[...rulesTranslation, ...rules]"
          :error-messages="errorMessagesTranslation"
      ></v-text-field>
    </v-sheet>
  `,
});

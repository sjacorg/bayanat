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
    rules: {
      type: Array,
      default: () => [v => true],
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
      isOriginalVisible: true,
      localOriginal: this.original,
      localTranslation: this.translation,
    };
  },
  watch: {
    // Watch for prop changes and update local copies accordingly
    original(newVal) {
      this.localOriginal = newVal;
    },
    translation(newVal) {
      this.localTranslation = newVal;
    },
  },
  methods: {
    toggleField() {
      this.isOriginalVisible = !this.isOriginalVisible;
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
          :rules="rules"
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
          :rules="rules"
      ></v-text-field>
    </v-sheet>
  `,
});

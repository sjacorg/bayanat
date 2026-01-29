const ToggleButton = Vue.defineComponent({
  props: {
    modelValue: { type: Boolean, default: false },
    readOnly: { type: Boolean, default: false },
    activeColor: { type: String, default: 'primary' },
    hideLeftIcon: { type: Boolean, default: false },
    closable: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    rounded: { type: String, default: () => null },
  },
  emits: ['update:modelValue', 'close'],

  computed: {
    variant() {
      if (this.modelValue) return 'tonal';
      if (this.readOnly) return 'tonal';
      return 'outlined';
    },

    buttonColor() {
      return this.modelValue ? this.activeColor : undefined;
    },

    buttonClasses() {
      return [
        'font-weight-medium',
        { 'text-medium-emphasis cursor-default': this.readOnly }
      ];
    },

    showLeftCheck() {
      return this.modelValue && !this.hideLeftIcon;
    },

    showLeftCross() {
      return !this.modelValue && this.readOnly && !this.hideLeftIcon;
    },
  },

  methods: {
    onClick() {
      if (!this.readOnly) {
        this.$emit('update:modelValue', !this.modelValue);
      }
    },
  },

  template: `
    <v-btn
      :variant="variant"
      :color="buttonColor"
      :class="buttonClasses"
      :readonly="readOnly"
      :disabled="disabled"
      @click="onClick"
      :rounded="rounded"
    >
      <template v-if="showLeftCheck">
        <v-icon start size="small">mdi-check</v-icon>
      </template>

      <template v-if="showLeftCross">
        <v-icon start size="small">mdi-close</v-icon>
      </template>

      <slot></slot>

      <v-icon
        v-if="closable"
        end
        size="small"
        @click.stop="$emit('close', modelValue)"
      >
        mdi-close-circle
      </v-icon>
    </v-btn>
  `,
});

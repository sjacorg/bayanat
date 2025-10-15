const ToggleButton = Vue.defineComponent({
  props: {
    modelValue: {
      type: Boolean,
      required: true,
      default: false,
    },
    activeColor: {
      type: String,
      default: 'primary',
    },
  },
  emits: ['update:modelValue'],
  template: `
    <v-btn
      :variant="modelValue ? 'tonal' : 'outlined'"
      :color="modelValue ? activeColor : undefined"
      @click="$emit('update:modelValue', !modelValue)"
    >
      <v-icon v-if="modelValue" start size="small">mdi-check</v-icon>
      <slot></slot>
    </v-btn>
  `,
});
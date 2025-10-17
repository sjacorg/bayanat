const ToggleButton = Vue.defineComponent({
  props: {
    modelValue: {
      type: Boolean,
      required: true,
      default: false,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    activeColor: {
      type: String,
      default: 'primary',
    },
    hideIcon: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue'],
  template: `
    <v-btn
      :variant="modelValue || (!modelValue && readOnly) ? 'tonal' : 'outlined'"
      :color="modelValue ? activeColor : undefined"
      @click="$emit('update:modelValue', !modelValue)"
      :class="['font-weight-medium', { 'text-medium-emphasis cursor-default': readOnly }]"
      read-only
      :ripple="!readOnly"
    >
      <template v-if="!hideIcon">
        <v-icon v-if="modelValue" start size="small">mdi-check</v-icon>
        <v-icon v-if="!modelValue && readOnly" start size="small">mdi-close</v-icon>
      </template>
      <slot></slot>
    </v-btn>
  `,
});
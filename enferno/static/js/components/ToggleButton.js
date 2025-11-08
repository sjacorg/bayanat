const ToggleButton = Vue.defineComponent({
  props: {
    modelValue: { type: Boolean, required: true, default: false },
    readOnly: { type: Boolean, default: false },
    activeColor: { type: String, default: 'primary' },
    hideLeftIcon: { type: Boolean, default: false },
    closable: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  },
  emits: ['update:modelValue', 'close'],
  template: `
    <v-btn
      :variant="modelValue || (!modelValue && readOnly) ? 'tonal' : 'outlined'"
      :color="modelValue ? activeColor : undefined"
      @click="$emit('update:modelValue', !modelValue)"
      :class="['font-weight-medium', { 'text-medium-emphasis cursor-default': readOnly }]"
      :readonly="readOnly"
      :disabled="disabled"
    >
      <template v-if="!hideLeftIcon">
        <v-icon v-if="modelValue" start size="small">mdi-check</v-icon>
        <v-icon v-if="!modelValue && readOnly" start size="small">mdi-close</v-icon>
      </template>
      <slot></slot>
      <v-icon v-if="closable" @click.stop="$emit('close', modelValue)" end size="small">mdi-close-circle</v-icon>
    </v-btn>
  `,
});
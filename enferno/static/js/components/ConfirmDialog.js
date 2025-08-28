const ConfirmDialog = Vue.defineComponent({
    props: {
        modelValue: { type: Boolean, default: false },
        title: { type: String, default: 'Confirm' },
        message: { type: String, default: 'Are you sure?' },
        cancelText: { type: String, default: 'Cancel' },
        confirmText: { type: String, default: 'Confirm' },
        color: { type: String, default: 'red' },
    },
    emits: ['update:model-value', 'confirm', 'cancel'],
    data() {
        return {
            open: this.modelValue,
        };
    },
    watch: {
        modelValue(val) {
            this.open = val;
        },
        open(val) {
            this.$emit('update:model-value', val);
        },
    },
    methods: {
        onCancel() {
            this.$emit('cancel');
            this.open = false;
        },
        onConfirm() {
            this.$emit('confirm');
            this.open = false;
        },
    },
    template: `
    <v-dialog v-model="open" max-width="450">
      <v-card>
        <v-card-title class="text-h6">
          <slot name="title">{{ title }}</slot>
        </v-card-title>

        <v-card-text>
          <slot name="message">{{ message }}</slot>
        </v-card-text>

        <v-card-actions class="justify-end">
          <slot name="actions">
            <v-btn text @click="onCancel">{{ cancelText }}</v-btn>
            <v-btn :color="color" dark @click="onConfirm">{{ confirmText }}</v-btn>
          </slot>
        </v-card-actions>
      </v-card>
    </v-dialog>
  `,
});

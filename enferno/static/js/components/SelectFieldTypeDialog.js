const SelectFieldTypeDialog = Vue.defineComponent({
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    entityType: {
      type: String,
      default: '',
    },
  },
  emits: ['update:modelValue', 'create'],
  data() {
    return {
      translations: window.translations,
      componentTypes: [
        {
          label: window.translations.shortText_,
          field_type: 'text',
          ui_component: 'input',
          icon: 'mdi-text-short',
          description: window.translations.upTo255Characters_,
        },
        {
          label: window.translations.longText_,
          field_type: 'long_text',
          ui_component: 'textarea',
          icon: 'mdi-text-long',
          description: window.translations.unlimitedTextLength_,
        },
        {
          label: window.translations.number_,
          field_type: 'number',
          ui_component: 'number_input',
          icon: 'mdi-numeric',
          description: window.translations.wholeNumbersOnly_,
        },
        {
          label: window.translations.dropdown_,
          field_type: 'select',
          ui_component: 'dropdown',
          icon: 'mdi-chevron-down-circle-outline',
          description: window.translations.singleOrMultipleChoice_,
        },
        {
          label: window.translations.dateAndTime_,
          field_type: 'datetime',
          ui_component: 'date_picker',
          icon: 'mdi-calendar-blank-outline',
          description: window.translations.dateWithOptionalTime_,
        },
      ]
    };
  },
  methods: {
    async create({ field_type, ui_component }) {
      try {
        const nextNumber = this.$root.formBuilder.dynamicFields[this.entityType].filter(field => !field.core).length + 1
        const sortOrders = this.$root.formBuilder.dynamicFields[this.entityType].map(f => f.sort_order ?? 0);
        const nextSort = (sortOrders.length ? Math.max(...sortOrders) : 0) + 1;

        const field = {
          id: `temp-${Date.now()}`, // temp ID if new
          name: `field_${nextNumber}`,
          title: this.translations.fieldN_(nextNumber),
          entity_type: this.entityType,
          field_type,
          ui_component,
          sort_order: nextSort,
          required: false,
          options: (field_type === 'select') ? [{ id: 1, label: this.translations.optionN_(1), hidden: false }] : null,
          schema_config: field_type === 'select' ? { allow_multiple: true } : {},
          ui_config: { width: 'w-100', help_text: '' },
          validation_config: {},
          active: true,
          searchable: true,
          core: false,
          deleted: null,
        };


        this.$emit('create', field);
        this.$emit('update:modelValue', false);
      } catch (err) {
        console.error('Error saving field:', err);
      }
    },
  },
  template: `
    <v-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" max-width="900">
      <v-card rounded="12">
        <v-card-title class="d-flex justify-space-between align-center px-7 pt-6 pb-0">
          {{ translations.selectFieldType_ }}
        </v-card-title>
        <v-card-text class="px-7 pb-7">
          <v-row :dense="false">
            <v-col v-for="({ label, field_type, ui_component, icon, description }) in componentTypes" cols="12" md="4">
              <v-card class="rounded-10 border border-opacity-25" rounded="10" variant="outlined" @click="create({ field_type, ui_component })">
                <v-card-item>
                  <template v-slot:prepend>
                    <v-icon class="mr-2" color="primary">{{ icon }}</v-icon>
                  </template>
                  <v-card-title class="text-body-2">{{ label }}</v-card-title>
                  <v-card-subtitle class="text-caption font-italic">{{ description }}</v-card-subtitle>
                </v-card-item>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-dialog>
  `,
});

window.SelectFieldTypeDialog = SelectFieldTypeDialog;

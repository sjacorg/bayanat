const SelectFieldTypeDialog = Vue.defineComponent({
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    dynamicFields: {
      type: Array,
      default: () => [],
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
          label: translations.shortText_,
          field_type: 'text',
          ui_component: 'input',
          icon: 'mdi-text-short',
        },
        {
          label: translations.longText_,
          field_type: 'long_text', 
          ui_component: 'textarea',
          icon: 'mdi-text-long',
        },
        {
          label: translations.number_,
          field_type: 'number',
          ui_component: 'number_input',
          icon: 'mdi-numeric',
        },
        {
          label: translations.dropdown_,
          field_type: 'single_select',
          ui_component: 'dropdown',
          icon: 'mdi-chevron-down-circle-outline',
        },
        {
          label: translations.multiSelect_ || 'Multi-Select',
          field_type: 'multi_select',
          ui_component: 'multi_dropdown',
          icon: 'mdi-format-list-checks',
        },
        {
          label: translations.dateAndTime_,
          field_type: 'datetime',
          ui_component: 'date_picker',
          icon: 'mdi-calendar-blank-outline',
        },
      ]
    };
  },
  methods: {
    async create({ field_type, ui_component }) {
      try {
        const nextNumber = this.dynamicFields.filter(field => !field.core).length + 1

        const field = {
          id: `temp-${Date.now()}`, // temp ID if new
          name: `field_${nextNumber}`,
          title: this.translations.fieldN_(nextNumber),
          entity_type: this.entityType,
          field_type,
          ui_component,
          sort_order: 0,
          required: false,
          options: (field_type === 'single_select' || field_type === 'multi_select') ? [{ id: 1, label: this.translations.optionN_(1), value: 'option_1', hidden: false }] : null,
          schema_config: {},
          ui_config: { width: 'w-100', help_text: '' },
          validation_config: {},
          active: true,
          searchable: false,
          core: false,
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
            <v-col v-for="({ label, field_type, ui_component, icon }) in componentTypes" cols="12" md="4">
              <v-card class="rounded-10 border border-opacity-25" rounded="10" variant="outlined" @click="create({ field_type, ui_component })">
                <v-card-text>
                  <v-icon size="large" class="mr-2" color="primary">{{ icon }}</v-icon>{{ label }}
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-dialog>
  `,
});

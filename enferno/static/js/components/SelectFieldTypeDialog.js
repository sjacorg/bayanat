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
          label: translations.shortText_,
          component: 'text_input',
          field: 'string',
          icon: 'mdi-text-short',
        },
        {
          label: translations.longText_,
          component: 'text_area',
          field: 'text',
          icon: 'mdi-text-long',
        },
        {
          label: translations.number_,
          component: 'number',
          field: 'integer',
          icon: 'mdi-numeric',
        },
        {
          label: translations.dropdown_,
          component: 'dropdown',
          field: 'string',
          icon: 'mdi-chevron-down-circle-outline',
        },
        {
          label: translations.dateAndTime_,
          component: 'date_picker',
          field: 'datetime',
          icon: 'mdi-calendar-blank-outline',
        },
      ]
    };
  },
  methods: {
    async create({ field_type, ui_component }) {
      try {
        const field = {
          id: `backup-${Date.now()}`, // temp ID if new
          name: '',
          title: '',
          entity_type: this.entityType,
          field_type,
          ui_component,
          sort_order: 0,
          required: false,
          options: ui_component === 'dropdown' ? [{label: '', value: ''}] : null,
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
            <v-col v-for="({ label, field, component, icon }) in componentTypes" cols="12" md="4">
              <v-card class="rounded-10 border border-opacity-25" rounded="10" variant="outlined" @click="create({ field_type: field, ui_component: component })">
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

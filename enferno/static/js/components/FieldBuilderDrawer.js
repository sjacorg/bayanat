const FieldBuilderDrawer = Vue.defineComponent({
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
  emits: ['update:modelValue', 'save'],
  data() {
    return {
      translations: window.translations,
      form: {
        name: '',
        title: '',
        entity_type: this.entityType,
        field_type: '',
        ui_component: '',
        schema_config: {},
        ui_config: { help_text: 'Enter value' },
        validation_config: {},
        options: [{ label: '', value: '' }],
        active: true,
        searchable: false,
      },
      fieldTypes: [
        {
          value: 'string',
          label: 'Short Text',
          interfaces: ['text_input', 'dropdown']
        },
        {
          value: 'text',
          label: 'Long Text',
          interfaces: ['text_area']
        },
        {
          value: 'integer',
          label: 'Number (Integer)',
          interfaces: ['number']
        },
        {
          value: 'float',
          label: 'Number (Decimal)',
          interfaces: ['number']
        },
        {
          value: 'datetime',
          label: 'Date & Time',
          interfaces: ['date_picker']
        },
        {
          value: 'boolean',
          label: 'True/False',
          interfaces: ['checkbox']
        },
        {
          value: 'array',
          label: 'Multiple Selection',
          interfaces: ['multi_select']
        },
        {
          value: 'json',
          label: 'JSON Data',
          interfaces: ['text_area']
        }
      ]
    };
  },
  computed: {
    selectedFieldType() {
      const type = this.fieldTypes.find((t) => t.value === this.form.field_type);
      return type;
    },
    availableInterfaces() {
      const type = this.fieldTypes.find((t) => t.value === this.form.field_type);
      return type?.interfaces || [];
    },
    currentFieldType() {
      return this.fieldTypes.find((t) => t.value === this.form.field_type);
    },
  },
  methods: {
    autoSelectInterface() {
      if (this.selectedFieldType?.interfaces?.includes(this.form.ui_component)) return;

      if (this.availableInterfaces.length > 0) {
        this.form.ui_component = this.availableInterfaces[0];
      }
    },
    populateForm(item) {
      this.form = {
        name: item.name || '',
        title: item.title || '',
        description: item.description || '',
        field_type: item.field_type || '',
        ui_component: item.ui_component || '',
        sort_order: item.sort_order || '',
        required: item.required ?? false,
        options: item.options?.length ? item.options : [{ label: '', value: '' }],
        schema_config: { ...item.schema_config },       // preserve existing schema config
        ui_config: { ...item.ui_config },               // preserve existing UI config
        validation_config: { ...item.validation_config }, // preserve existing validation config
        active: item.active ?? true,
        searchable: item.schema_config?.searchable ?? false,
      };
    },
    async saveField() {
      try {
        const field = {
          id: this.item?.id ?? `backup-${Date.now()}`, // temp ID if new
          name: this.form.name,
          title: this.form.title,
          entity_type: this.entityType,
          field_type: this.form.field_type,
          ui_component: this.form.ui_component,
          sort_order: Number(this.form.sort_order || 0),
          required: this.form.required ?? false,
          options: (this.form.options ?? []).filter(opt => opt?.label && opt?.value),
          schema_config: { ...this.form.schema_config },
          ui_config: { ...this.form.ui_config },
          validation_config: { ...this.form.validation_config },
          active: this.form.active ?? true,
          searchable: this.form.schema_config?.searchable ?? false,
          core: this.item?.core ?? false,
          created_at: this.item?.created_at,
        };


        this.$emit('save', field);
        this.$emit('update:modelValue', false);
      } catch (err) {
        console.error('Error saving field:', err);
      }
    },
  },
  watch: {
    'form.field_type'() {
      this.autoSelectInterface();
    },
    modelValue(newVal) {
      if (newVal) {
        this.populateForm({}); // clear form
      }
    },
  },
  template: `
    <v-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" max-width="900">
      <v-card>
        <v-card-title class="d-flex justify-space-between align-center">
          {{ translations.selectFieldType_ }}
        </v-card-title>
        <v-card-text>
          <v-row :dense="false">
            <v-col cols="12" md="4"><v-card variant="outlined"><v-card-text><v-icon class="mr-2" color="primary">mdi-text-short</v-icon>{{ translations.shortText_ }}</v-card-text></v-card></v-col>
            <v-col cols="12" md="4"><v-card variant="outlined"><v-card-text><v-icon class="mr-2" color="primary">mdi-text-long</v-icon>{{ translations.longText_ }}</v-card-text></v-card></v-col>
            <v-col cols="12" md="4"><v-card variant="outlined"><v-card-text><v-icon class="mr-2" color="primary">mdi-numeric</v-icon>{{ translations.number_ }}</v-card-text></v-card></v-col>
            <v-col cols="12" md="4"><v-card variant="outlined"><v-card-text><v-icon class="mr-2" color="primary">mdi-chevron-down-circle-outline</v-icon>{{ translations.dropdown_ }}</v-card-text></v-card></v-col>
            <v-col cols="12" md="4"><v-card variant="outlined"><v-card-text><v-icon class="mr-2" color="primary">mdi-calendar-blank-outline</v-icon>{{ translations.dateAndTime_ }}</v-card-text></v-card></v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-dialog>
  `,
});

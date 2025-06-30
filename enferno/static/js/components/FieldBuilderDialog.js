const FieldBuilderDialog = Vue.defineComponent({
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['update:modelValue'],
  data() {
    return {
      translations: window.translations,
      currentTab: 'details',
      form: {
        name: '',
        title: '',
        description: '',
        field_type: '',
        ui_component: '',
        options: [],
        schema_config: {
          required: false,
          default: null,
          max_length: null
        },
        ui_config: {
          label: '',
          help_text: '',
          sort_order: 1,
          readonly: false,
          hidden: false
        },
        validation_config: {
          max_length: null,
          min: null,
          max: null,
          precision: null,
          scale: null,
          format: ''
        }
      },
      tabs: [
        {id: 'details', label: 'Field Details', icon: 'mdi-form-textbox'},
        {id: 'schema', label: 'Schema', icon: 'mdi-database'},
        {id: 'interface', label: 'Interface', icon: 'mdi-palette'},
        {id: 'validation', label: 'Validation', icon: 'mdi-check-circle'}
      ],
      fieldTypes: [
        {
          value: 'string', 
          label: 'Text Input',
          description: 'Short text field',
          interfaces: ['text_input', 'dropdown']
        },
        {
          value: 'text', 
          label: 'Text Area',
          description: 'Long text content',
          interfaces: ['text_area']
        },
        {
          value: 'integer', 
          label: 'Integer',
          description: 'Whole numbers',
          interfaces: ['number']
        },
        {
          value: 'float', 
          label: 'Float',
          description: 'Decimal numbers',
          interfaces: ['number']
        },
        {
          value: 'datetime', 
          label: 'Date & Time',
          description: 'Date and time values',
          interfaces: ['date_picker']
        },
        {
          value: 'boolean', 
          label: 'Boolean',
          description: 'True/false values',
          interfaces: ['checkbox']
        },
        {
          value: 'array', 
          label: 'Multi Select',
          description: 'Multiple choice values',
          interfaces: ['multi_select']
        },
        {
          value: 'json', 
          label: 'JSON',
          description: 'Structured data',
          interfaces: ['text_area']
        }
      ]
    }
  },
  computed: {
    availableInterfaces() {
      const type = this.fieldTypes.find(t => t.value === this.form.field_type);
      return type?.interfaces || [];
    },
    currentFieldType() {
      return this.fieldTypes.find(t => t.value === this.form.field_type);
    }
  },
  methods: {
    switchTab(tabId) {
      this.currentTab = tabId;
    },
    autoSelectInterface() {
      if (this.availableInterfaces.length > 0) {
        this.form.ui_component = this.availableInterfaces[0];
      }
    },
    validateForm() {
      // Validate current tab before allowing navigation
      return true;
    },
    async saveField() {
      // POST or PATCH to API
    }
  },
  watch: {
    'form.field_type'() {
      this.autoSelectInterface();
    }
  },
  template: `
        <v-dialog
          :model-value="modelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          max-width="800"
        >
          <v-card
            prepend-icon="mdi-account"
            title="Field builder"
          >

            <v-tabs
              v-model="currentTab"
              color="primary"
            >
              <v-tab :value="tab.id" v-for="(tab, index) in tabs" :key="tab.id"><v-icon class="mr-2">{{ tab.icon }}</v-icon>{{ tab.label }}</v-tab>
            </v-tabs>
    
            <v-card-text>
              <v-tabs-window v-model="currentTab">
                <v-tabs-window-item value="details">
                  <v-row dense>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        label="Field title*"
                        required
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        label="Field name*"
                        required
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        label="Help text/description*"
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-select
                        label="Field type*"
                        :options="fieldTypes"
                        item-label="label"
                        item-value="value"
                      ></v-select>
                    </v-col>
                  </v-row>
                </v-tabs-window-item>

                <v-tabs-window-item value="schema">
                  schema-config
                </v-tabs-window-item>

                <v-tabs-window-item value="interface">
                  interface
                </v-tabs-window-item>

                <v-tabs-window-item value="validation">
                  validation
                </v-tabs-window-item>
              </v-tabs-window>
            </v-card-text>

            <v-divider></v-divider>

            <v-card-actions>
              <v-spacer></v-spacer>

              <v-btn
                variant="outlined"
                @click="$emit('update:modelValue', false)"
              >Cancel</v-btn>

              <v-btn
                color="primary"
                variant="flat"
                prepend-icon="mdi-check"
                @click="$emit('update:modelValue', false)"
              >{{ translations.save_ }}</v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
  `,
});

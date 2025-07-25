const FieldBuilderDrawer = Vue.defineComponent({
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
        options: [{ label: null, value: null }],
        schema_config: {
          required: false,
          searchable: false,
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
      try {
        axios.post('/admin/api/dynamic-fields', this.form).response(response => {
          console.log('Field saved successfully:', response.data);
        })
      } catch (err) {
        console.error('Error saving field:', err);
        this.showSnack(handleRequestError(err))
      }
    }
  },
  watch: {
    'form.field_type'() {
      this.autoSelectInterface();
    }
  },
  template: `
        <v-navigation-drawer
          :model-value="modelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          clipped
          fixed
          location="right"
          temporary
          width="600"
          app
          disable-route-watcher
        >
          <v-card
            prepend-icon="mdi-account"
            title="Field builder"
            flat
          >

            <v-tabs
              :modelValue="currentTab"
              @update:modelValue="switchTab"
              color="primary"
            >
              <v-tab :value="tab.id" v-for="(tab, index) in tabs" :key="tab.id"><v-icon class="mr-2">{{ tab.icon }}</v-icon>{{ tab.label }}</v-tab>
            </v-tabs>
    
            <v-tabs-window v-model="currentTab">
              <v-tabs-window-item value="details">
                <v-card-text>
                  <v-row dense>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.title"
                        label="Field title*"
                        required
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.name"
                        label="Field name*"
                        required
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.description"
                        label="Help text/description"
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-select
                        v-model="form.field_type"
                        label="Field type*"
                        :items="fieldTypes"
                        item-title="label"
                        item-value="value"
                      ></v-select>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-tabs-window-item>

              <v-tabs-window-item value="schema">
                <v-card-text>
                  <v-row dense>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.schema_config.default"
                        label="Default value"
                      ></v-text-field>
                    </v-col>
                    <v-col
                      v-if="form.field_type === 'string'"
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.schema_config.max_length"
                        label="Max length"
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-switch v-model="form.schema_config.required" color="primary" label="Mark as required"></v-switch>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-switch v-model="form.schema_config.searchable" color="primary" label="Mark as searchable"></v-switch>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-tabs-window-item>

              <v-tabs-window-item value="interface">
                <v-card-text>
                  <v-row dense>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.ui_component"
                        label="UI Component*"
                        disabled
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.ui_config.label"
                        label="Label*"
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.ui_config.help_text"
                        label="Help text"
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.ui_config.sort_order"
                        label="Sort order"
                        type="number"
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-switch v-model="form.ui_config.readonly" color="primary" label="Readonly"></v-switch>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-switch v-model="form.ui_config.hidden" color="primary" label="Hidden"></v-switch>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-tabs-window-item>

              <v-tabs-window-item value="validation">
                <v-card-text>
                  <v-row dense>
                    <v-col
                      v-if="form.field_type === 'string' || form.field_type === 'text'"
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.validation_config.max_length"
                        label="Max length"
                      ></v-text-field>
                    </v-col>
                    <template v-else-if="form.field_type === 'integer' || form.field_type === 'float'">
                      <v-col
                        cols="12"
                        md="6"
                      >
                        <v-text-field
                          v-model="form.validation_config.min"
                          label="Minimum value"
                        ></v-text-field>
                      </v-col>
                      <v-col
                        cols="12"
                        md="6"
                      >
                        <v-text-field
                          v-model="form.validation_config.max"
                          label="Maximum value"
                        ></v-text-field>
                      </v-col>
                      <template v-if="form.field_type === 'float'">
                        <v-col
                          cols="12"
                          md="6"
                        >
                          <v-text-field
                            v-model="form.validation_config.precision"
                            label="Precision"
                          ></v-text-field>
                        </v-col>
                        <v-col
                          cols="12"
                          md="6"
                        >
                          <v-text-field
                            v-model="form.validation_config.scale"
                            label="Scale"
                          ></v-text-field>
                        </v-col>
                      </template>
                    </template>
                    <v-col
                      v-else-if="form.field_type === 'datetime'"
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        v-model="form.validation_config.format"
                        label="Format"
                      ></v-text-field>
                    </v-col>
                    <v-col
                      v-else-if="form.field_type === 'array'"
                      cols="12"
                    >
                      <v-card>
                        <v-toolbar>
                          <v-toolbar-title>Options</v-toolbar-title>
                          <v-spacer></v-spacer>
                          <v-btn
                            color="primary"
                            icon="mdi-plus-circle"
                          ></v-btn>
                        </v-toolbar>
                        <v-card-text v-for="(option, index) in form.options" :key="index" class="pt-0">
                          <v-row dense>
                            <v-col
                              cols="12"
                              md="6"
                            >
                              <v-text-field
                                v-model="option.label"
                                label="Label"
                              ></v-text-field>
                            </v-col>
                            <v-col
                              cols="12"
                              md="6"
                            >
                              <v-text-field
                                v-model="option.value"
                                label="Value"
                              ></v-text-field>
                            </v-col>
                          </v-row>
                        </v-card-text>
                      </v-card>
                    </v-col>
                    <v-col
                      v-else
                      cols="12"
                      md="6"
                    >
                      No additional validation options available for this field type.
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-tabs-window-item>
            </v-tabs-window>

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
                @click="saveField()"
              >{{ translations.save_ }}</v-btn>
            </v-card-actions>
          </v-card>
        </v-navigation-drawer>
  `,
});

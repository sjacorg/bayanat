const FieldBuilderDrawer = Vue.defineComponent({
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    item: {
      type: Object,
      default: null,
    },
    entityType: {
      type: String,
      default: '',
    }
  },
  emits: ['update:modelValue', 'save'],
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
        { id: 'details', label: 'Field Details', icon: 'mdi-form-textbox' },
        { id: 'schema', label: 'Schema', icon: 'mdi-database' },
        { id: 'interface', label: 'Interface', icon: 'mdi-palette' },
        { id: 'validation', label: 'Validation', icon: 'mdi-check-circle' }
      ],
      fieldTypes: [
        {
          value: 'string',
          label: 'Text Input',
          description: 'Short text field',
          interfaces: ['input', 'dropdown']
        },
        {
          value: 'text',
          label: 'Text Area',
          description: 'Long text content',
          interfaces: ['textarea']
        },
        {
          value: 'integer',
          label: 'Integer',
          description: 'Whole numbers',
          interfaces: ['input']
        },
        {
          value: 'float',
          label: 'Float',
          description: 'Decimal numbers',
          interfaces: ['input']
        },
        {
          value: 'datetime',
          label: 'Date & Time',
          description: 'Date and time values',
          interfaces: ['date']
        },
        {
          value: 'boolean',
          label: 'Boolean',
          description: 'True/false values',
          interfaces: ['checkbox', 'switch']
        },
        {
          value: 'array',
          label: 'Multi Select',
          description: 'Multiple choice values',
          interfaces: ['textarea']
        },
        {
          value: 'json',
          label: 'JSON',
          description: 'Structured data',
          interfaces: ['textarea']
        }
      ]
    };
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
    populateForm(item) {
      this.form = {
        name: item.name || '',
        title: item.title || '',
        description: item.description || '',
        field_type: item.field_type || '',
        ui_component: item.ui_component || '',
        options: item.options?.length ? item.options : [{ label: null, value: null }],
        schema_config: {
          required: item.schema_config?.required ?? false,
          searchable: item.schema_config?.searchable ?? false,
          default: item.schema_config?.default ?? null,
          max_length: item.schema_config?.max_length ?? null
        },
        ui_config: {
          label: item.ui_config?.label || '',
          help_text: item.ui_config?.help_text || '',
          sort_order: item.ui_config?.sort_order ?? 1,
          readonly: item.ui_config?.readonly ?? false,
          hidden: item.ui_config?.hidden ?? false
        },
        validation_config: {
          max_length: item.validation_config?.max_length ?? null,
          min: item.validation_config?.min ?? null,
          max: item.validation_config?.max ?? null,
          precision: item.validation_config?.precision ?? null,
          scale: item.validation_config?.scale ?? null,
          format: item.validation_config?.format ?? ''
        }
      };
    },
    async saveField() {
      try {
        const field = {
          id: this.item?.id ?? Date.now(),
          name: this.form.name,
          title: this.form.title,
          entity_type: this.entityType,
          field_type: this.form.field_type,
          ui_component: this.form.ui_component,
          options: this.form.options?.length ? this.form.options : undefined,
          schema_config: {
            required: this.form.schema_config.required,
            searchable: this.form.schema_config.searchable,
            max_length: this.form.schema_config.max_length ?? undefined,
            default: this.form.schema_config.default ?? undefined
          },
          ui_config: {
            sort_order: this.form.ui_config.sort_order,
            help_text: this.form.ui_config.help_text,
            label: this.form.ui_config.label,
            readonly: this.form.ui_config.readonly,
            hidden: this.form.ui_config.hidden
          },
          validation_config: { ...this.form.validation_config },
          active: true,
          created_at: this.item?.created_at ?? new Date().toISOString()
        };

        this.$emit('save', field);
        this.$emit('update:modelValue', false);
      } catch (err) {
        console.error('Error saving field:', err);
      }
    }
  },
  watch: {
    'form.field_type'() {
      this.autoSelectInterface();
    },
    modelValue(newVal) {
      if (newVal) {
        if (this.item) {
          this.populateForm(this.item);
        } else {
          this.populateForm({}); // clear form
        }
      }
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

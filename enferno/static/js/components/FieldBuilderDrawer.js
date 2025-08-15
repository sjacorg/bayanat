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
    },
  },
  emits: ['update:modelValue', 'save'],
  data() {
    return {
      validationRules: validationRules,
      translations: window.translations,
      currentTab: 'details',
      valid: false,
      form: {
        name: '',
        title: '',
        entity_type: this.entityType,
        field_type: '',
        ui_component: '',
        schema_config: { required: false },
        ui_config: { help_text: 'Enter value' },
        validation_config: {},
        options: [],
        active: true,
        searchable: false,
      },
      tabs: [
        { id: 'details', label: 'Field Details', icon: 'mdi-form-textbox' },
        { id: 'schema', label: 'Schema', icon: 'mdi-database' },
        { id: 'validation', label: 'Validation', icon: 'mdi-check-circle' },
      ],
      fieldTypes: [
  {
    value: 'string',
    label: 'Short Text',
    interfaces: ['text_input', 'dropdown']
  },
  {
    value: 'text', 
    label: 'Long Text',
    interfaces: ['text_area', 'editor']
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
    isNewField() {
      return !Boolean(this.item?.id)
    },
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
    validateForm() {
      this.$refs.form.validate().then(({ valid, errors }) => {
        if (valid) {
          this.saveField();
        } else {
          this.$root.showSnack(translations.pleaseReviewFormForErrors_);
          scrollToFirstError(errors);
        }
      });
    },
    switchTab(tabId) {
      this.currentTab = tabId;
    },
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
        options: item.options?.length ? item.options : [],
        schema_config: {},
        ui_config: {},
        validation_config: {},
      };
    },
    async saveField() {
      try {
        const field = {
          id: this.item?.id,
          name: this.form.name,
          title: this.form.title,
          entity_type: this.entityType,
          field_type: this.form.field_type,
          ui_component: this.form.ui_component,
          options: this.form.options?.length ? this.form.options : undefined,
          schema_config: {},
          ui_config: {},
          validation_config: {},
          active: true,
          created_at: this.item?.created_at ?? new Date().toISOString(),
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
        this.currentTab = 'details';
        if (this.item) {
          this.populateForm(this.item);
        } else {
          this.populateForm({}); // clear form
        }
      }
    },
  },
  template: `
        <v-navigation-drawer
          v-if="modelValue"
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
          <v-form ref="form" v-model="valid">
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
                        :rules="[validationRules.required()]"
                      ></v-text-field>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-text-field
                        :disabled="!isNewField"
                        v-model="form.name"
                        label="Field name*"
                        required
                        :rules="[validationRules.required()]"
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
                        :rules="[validationRules.required()]"
                      ></v-select>
                    </v-col>
                    <v-col
                      cols="12"
                      md="6"
                    >
                      <v-select
                        v-model="form.ui_component"
                        label="UI Component*"
                        :disabled="availableInterfaces.length <= 1"
                        :items="availableInterfaces"
                        :rules="[validationRules.required()]"
                      ></v-select>
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

              <v-tabs-window-item value="validation">
                <v-card-text>
                  <v-row dense>
                    <v-col
                      v-if="['input', 'editor', 'textarea'].includes(form.ui_component)"
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
                      v-else-if="form.ui_component === 'dropdown'"
                      cols="12"
                    >
                      <v-card>
                        <v-toolbar>
                          <v-toolbar-title>Options</v-toolbar-title>
                          <v-spacer></v-spacer>
                          <v-btn
                            color="primary"
                            icon="mdi-plus-circle"
                            @click="form.options.push({ label: '', value: '' })"
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
                @click="validateForm()"
              >{{ translations.save_ }}</v-btn>
            </v-card-actions>
          </v-card>
          </v-form>
        </v-navigation-drawer>
  `,
});

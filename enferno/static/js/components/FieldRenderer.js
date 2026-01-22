const FieldRenderer = Vue.defineComponent({
    props: ['field', 'modelValue'],
    emits: ['update:modelValue'],
    data() {
        return {
            translations: window.translations,
            validationRules,
        }
    },
    computed: {
        componentProps() {
            return this.mapFieldToComponent(this.field)
        },
    },
    methods: {
        buildValidationRules(field) {
            const rules = []
            const maxLength = Number(field?.validation_config?.max_length)
            const required = Boolean(field?.required)

            // Enforce max length (≤255 or default 255 for text)
            if (maxLength > 0 && maxLength <= 255) {
                rules.push(this.validationRules.maxLength(maxLength))
            } else if (field.field_type === 'text') {
                rules.push(this.validationRules.maxLength(255))
            }
            if (required) {
                rules.push(this.validationRules.required())
            }

            return rules
        },
        mapFieldToComponent(field) {
            const POSTGRES_INT_MIN = -2147483648
            const POSTGRES_INT_MAX = 2147483647

            const baseProps = {
                fieldId: field.id,
                label: field.title || this.translations.newField_,
                name: field.name,
                modelValue: this.modelValue ?? field.schema_config?.default ?? null,
                'onUpdate:modelValue': (newValue) => this.$emit('update:modelValue', newValue),
                disabled: !field.active,
                hint: field?.ui_config?.help_text,
                persistentHint: false,
                rules: this.buildValidationRules(field),
                variant: 'outlined',
                class: 'h-100'
            };

            const numberProps = {
                precision: field.field_type === 'float'
                    ? Number(field?.validation_config?.precision) || null
                    : 0,
                // always enforce Postgres integer range, but allow stricter overrides
                min: Math.max(
                    field?.validation_config?.min ?? POSTGRES_INT_MIN,
                    POSTGRES_INT_MIN
                ),
                max: Math.min(
                    field?.validation_config?.max ?? POSTGRES_INT_MAX,
                    POSTGRES_INT_MAX
                ),
                controlVariant: 'hidden',
                modelValue: (() => {
                    const value = this.modelValue ?? field.schema_config?.default

                    if (value === "" || value === undefined || value === null) return null
                    const num = Number(value)
                    return isNaN(num) ? null : num
                })(),
            };

            const componentMap = {
                input: { component: 'v-text-field', ...baseProps },
                textarea: { component: 'v-textarea', ...baseProps },
                number_input: { component: 'v-number-input', ...baseProps, ...numberProps },
                dropdown: {
                    component: 'v-select',
                    ...baseProps,
                    modelValue: Array.isArray(this.modelValue)
                                    ? this.modelValue.map(Number)
                                    : this.modelValue != null
                                        ? Number(this.modelValue)
                                        : field.schema_config?.default ?? null,
                    'onUpdate:modelValue': (newValue) => {
                        const normalized = field.schema_config?.allow_multiple
                            ? newValue
                            : newValue != null
                            ? [newValue]
                            : [];
                        this.$emit('update:modelValue', normalized);
                    },
                    items: field?.options?.filter(option => !option.hidden) || [],
                    'item-title': 'label',
                    'item-value': 'id',
                    chips: true,
                    clearable: true,
                    multiple: field.schema_config?.allow_multiple || false,
                    closableChips: field.schema_config?.allow_multiple || false
                },
                date_picker: { component: 'pop-date-time-field', ...baseProps },
                html_block: {
                    component: 'v-text-field',
                    ...baseProps,
                    modelValue: `Complex component: ${field.ui_config?.html_template || field.name}`,
                    readonly: true
                },
            };

            return componentMap[field.ui_component] || null;
        },
    },
    template: `
        <div>
            <v-hover>
                <template v-slot:default="{ isHovering, props }">
                    <div v-bind="props">
                        <component :is="componentProps.component" v-bind="{ ...componentProps, persistentHint: isHovering }"></component>
                    </div>
                </template>
            </v-hover>
        </div>
    `,
});
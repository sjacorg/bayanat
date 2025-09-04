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

            if (maxLength > 0) {
                rules.push(this.validationRules.maxLength(maxLength))
            }
            if (required) {
                rules.push(this.validationRules.required())
            }

            return rules
        },
        mapFieldToComponent(field) {
            const baseProps = {
                fieldId: field.id,
                label: field.title || this.translations.newField_,
                name: field.name,
                modelValue: this.modelValue || field.schema_config?.default || null,
                'onUpdate:modelValue': (newValue) => this.$emit('update:modelValue', newValue),
                disabled: !field.active,
                hint: field?.ui_config?.help_text,
                rules: this.buildValidationRules(field),
                variant: 'outlined'
            };

            const numberProps = {
                precision: field.field_type === 'float'
                    ? Number(field?.validation_config?.precision) || null
                    : 0,
                min: field?.validation_config?.min,
                max: field?.validation_config?.max,
                controlVariant: 'hidden',
            };

            const componentMap = {
                input: { component: 'v-text-field', ...baseProps },
                textarea: { component: 'v-textarea', ...baseProps },
                number_input: { component: 'v-number-input', ...baseProps, ...numberProps },
                dropdown: {
                    component: 'v-select',
                    ...baseProps,
                    items: field.options,
                    'item-title': 'label',
                    'item-value': 'value',
                    multiple: false
                },
                multi_dropdown: {
                    component: 'v-select',
                    ...baseProps,
                    items: field.options,
                    'item-title': 'label',
                    'item-value': 'value',
                    multiple: true
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
    template: /*html*/`
        <div>
            <component :is="componentProps.component" v-bind="componentProps"></component>
        </div>
    `,
});
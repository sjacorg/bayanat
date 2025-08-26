const iconMap = {
    text_input: 'mdi-text-short',
    text_area: 'mdi-text-long',
    dropdown: 'mdi-chevron-down-circle-outline',
    number: 'mdi-numeric',
    date_picker: 'mdi-calendar-blank-outline',
    multi_select: 'mdi-checkbox-multiple-marked-circle-outline',
}

const FieldListItem = Vue.defineComponent({
    props: ['field', 'dragging'],
    emits: ['edit', 'delete', 'toggle-visibility'],
    computed: {
        componentProps() {
            return this.mapFieldToComponent(this.field)
        }
    },
    methods: {
        mapFieldToComponent(field) {
            const baseProps = {
                fieldId: field.id,
                label: field.title,
                name: field.name,
                modelValue: field.schema_config?.default ?? null,
                variant: 'filled',
                disabled: !field.active,
                hint: field?.ui_config?.help_text,
                hideDetails: true,
                prependInnerIcon: iconMap[field.ui_component]
            };

            const numberProps = {
                precision: field.field_type === 'float'
                    ? Number(field?.validation_config?.precision) || null
                    : 0,
                min: field?.validation_config?.min,
                max: field?.validation_config?.max,
            };

            const componentMap = {
                number: { component: 'v-number-input', ...baseProps, ...numberProps },
                text_input: { component: 'v-text-field', ...baseProps },
                multi_select: {
                    component: 'v-select',
                    ...baseProps,
                    items: field.options,
                    'item-title': 'label',
                    'item-value': 'value',
                    multiple: field.field_type === 'array'
                },
                dropdown: {
                    component: 'v-select',
                    ...baseProps,
                    items: field.options,
                    'item-title': 'label',
                    'item-value': 'value',
                    multiple: field.field_type === 'array'
                },
                text_area: { component: 'v-textarea', ...baseProps },
                checkbox: { component: 'v-checkbox', ...baseProps },
                switch: { component: 'v-switch', ...baseProps },
                date_picker: { component: 'pop-date-time-field' },
                editor: {
                    component: 'tinymce-editor',
                    init: tinyConfig,
                    disabled: !field.active,
                    fieldId: field.id
                },
            };

            return componentMap[field.ui_component] || null;
        },
    },
    template: /*html*/ `
    <v-hover v-if="componentProps">
        <template v-slot:default="{ isHovering, props }">
            <div v-bind="props" class="d-flex flex-column ga-1 px-6 pb-6">
                <div :class="['d-flex justify-space-between align-center opacity-0', { 'opacity-100': isHovering && !dragging }]">
                    <div>
                        Width:
                        <v-btn-toggle color="primary" mandatory density="compact" variant="outlined" divided rounded>
                            <v-btn>
                                Full
                            </v-btn>

                            <v-btn>
                                Half
                            </v-btn>
                        </v-btn-toggle>
                    </div>

                    <v-icon class="drag-handle cursor-grab" size="large">mdi-drag-horizontal</v-icon>

                    <div v-if="!componentProps?.readonly" class="d-flex ga-4">
                        <v-btn density="comfortable" :disabled="field.core" icon @click="$emit('edit', { field, componentProps })" size="small"><v-icon>mdi-asterisk</v-icon></v-btn>
                        <v-btn density="comfortable" :disabled="field.core" icon @click="$emit('edit', { field, componentProps })" size="small"><v-icon>mdi-magnify</v-icon></v-btn>
                        <v-btn density="comfortable" icon @click="$emit('toggle-visibility', { field, componentProps })" size="small"><v-icon>{{ componentProps.disabled ? 'mdi-eye-outline' : 'mdi-eye-off-outline' }}</v-icon></v-btn>
                        <v-btn density="comfortable" :disabled="field.core" icon @click="$emit('delete', { field, componentProps })" size="small"><v-icon>mdi-trash-can-outline</v-icon></v-btn>
                    </div>
                </div>

                <component :is="componentProps.component" v-bind="componentProps" />
            </div>
        </template>
    </v-hover>

    <div v-else>Field data not provided</div>
    `,
});
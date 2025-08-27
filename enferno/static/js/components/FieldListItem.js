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
    emits: ['delete', 'toggle-visibility', 'width'],
    data: () => ({
        translations: window.translations,
        editingMode: false,
        width: this.field?.ui_config?.width || 'w-100'
    }),
    computed: {
        componentProps() {
            return this.mapFieldToComponent(this.field)
        }
    },
    methods: {
        mapFieldToComponent(field) {
            const baseProps = {
                fieldId: field.id,
                label: field.title || 'New Field',
                name: field.name,
                modelValue: field.schema_config?.default ?? null,
                variant: 'filled',
                disabled: !field.active,
                hint: field?.ui_config?.help_text,
                hideDetails: true,
                prependInnerIcon: iconMap[field.ui_component],
                appendInner: 'ok',
                'data-field-id': field.id,
                readonly: true,
                bgColor: !this.$vuetify.theme.global.current.dark && field.core ? 'core-field-accent' : undefined
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
    watch: {
        width(nextWidth) {
            // Ensure ui_config exists (without overwriting existing properties), then update width property
            (this.field.ui_config ??= {}).width = nextWidth ?? 'w-100'
        }
    },
    template: /*html*/`
    <v-hover v-if="componentProps">
        <template v-slot:default="{ isHovering, props }">
            <div v-bind="props" v-click-outside="() => this.editingMode = false" class="d-flex flex-column ga-1 px-6 pb-6 position-relative rounded-16 overflow-hidden">
                <v-slide-x-transition>
                    <div v-if="editingMode" class="position-absolute top-0 left-0 h-100 bg-primary" style="width: 10px;"></div>
                </v-slide-x-transition>

                <div :class="['d-flex justify-space-between align-center opacity-0', { 'opacity-100': editingMode || (isHovering && !dragging), 'pointer-events-none': dragging }]">
                    <div>
                        Width:
                        <v-btn-toggle v-model="width" color="primary" mandatory density="compact" variant="outlined" divided rounded>
                            <v-btn value="w-100">
                                Full
                            </v-btn>
                            <v-btn value="w-50">
                                Half
                            </v-btn>
                        </v-btn-toggle>
                    </div>

                    <v-icon class="drag-handle cursor-grab" size="large">mdi-drag-horizontal</v-icon>

                    <div class="d-flex ga-4">
                        <v-tooltip location="top">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" density="comfortable" variant="flat" icon size="small"><v-icon>mdi-asterisk</v-icon></v-btn>
                            </template>
                            {{ translations.markFieldAsRequired_ }}
                        </v-tooltip>
                        <v-tooltip location="top">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" density="comfortable" variant="flat" icon size="small"><v-icon>mdi-magnify</v-icon></v-btn>
                            </template>
                            {{ translations.markFieldAsSearchable_ }}
                        </v-tooltip>
                        <v-tooltip location="top">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" density="comfortable" variant="flat" icon @click="$emit('toggle-visibility', { field, componentProps })" size="small"><v-icon>{{ componentProps.disabled ? 'mdi-eye-outline' : 'mdi-eye-off-outline' }}</v-icon></v-btn>
                            </template>
                            {{ field.active ? translations.hideField_ : translations.showField_ }}
                        </v-tooltip>
                        <v-tooltip location="top">
                            <template v-slot:activator="{ props }">
                                <span v-bind="props">
                                    <v-btn density="comfortable" variant="flat" :disabled="field.core" icon @click="$emit('delete', { field, componentProps })" size="small"><v-icon>mdi-trash-can-outline</v-icon></v-btn>
                                </span>
                            </template>
                            {{ field.core ? translations.deletionRestricted_ : translations.deleteField_ }}
                        </v-tooltip>
                    </div>
                </div>

                <div v-if="!editingMode" :class="{'cursor-pointer': !dragging }" @click="editingMode = true">
                    <div class="pointer-events-none">
                        <component :is="componentProps.component" v-bind="componentProps">
                            <template #append-inner>
                                <v-chip v-if="field.core" variant="outlined" color="purple-lighten-1" class="rounded">
                                    DEFAULT
                                </v-chip>
                                <v-chip v-else variant="outlined" class="rounded">
                                    CUSTOM
                                </v-chip>
                            </template>
                        </component>
                    </div>
                </div>
                <div v-else>
                    <v-text-field variant="filled" label="Field label" v-model="field.title"></v-text-field>

                    <v-row>
                        <v-col v-if="field.ui_component === 'dropdown'" cols="12" md="6">
                            <div class="d-flex align-center">
                                <div class="text-h6 text-primary">Field Options</div>
                            </div>
                        </v-col>
                        <v-col cols="12" md="6">
                            <div class="text-h6 text-primary">Field Properties</div>
                        </v-col>
                    </v-row>
                </div>
            </div>
        </template>
    </v-hover>

    <div v-else>Field data not provided</div>
    `,
});
const iconMap = {
    input: 'mdi-text-short',
    textarea: 'mdi-text-long', 
    dropdown: 'mdi-chevron-down-circle-outline',
    number_input: 'mdi-numeric',
    date_picker: 'mdi-calendar-blank-outline',
    multi_dropdown: 'mdi-format-list-checks',
}

const FieldListItem = Vue.defineComponent({
    props: ['field', 'dragging'],
    emits: ['delete', 'toggle-visibility', 'width'],
    data() {
        return {
            translations: window.translations,
            editingMode: false,
        }
    },
    computed: {
        componentProps() {
            return this.mapFieldToComponent(this.field)
        },
        widthProxy: {
            get() {
                return this.field?.ui_config?.width || 'w-100'
            },
            set(val) {
                (this.field.ui_config ??= {}).width = val
            }
        },
        dropdownOptionsProxy: {
            get() {
                return (this.field?.ui_component === 'dropdown' || this.field?.ui_component === 'multi_dropdown')
                    ? this.field?.options || [{ label: '', value: '' }]
                    : null
            },
            set(val) {
                this.field.options = val
            }
        }
    },
    methods: {
        mapFieldToComponent(field) {
            const baseProps = {
                fieldId: field.id,
                label: field.title || this.translations.newField_,
                name: field.name,
                modelValue: field.schema_config?.default ?? null,
                variant: 'filled',
                disabled: !field.active,
                hint: field?.ui_config?.help_text,
                hideDetails: true,
                prependInnerIcon: iconMap[field.ui_component],
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
                date_picker: { component: 'pop-date-time-field' },
            };

            return componentMap[field.ui_component] || null;
        },
        updateDropdownOption(nextValue, option, index) {
            const originalField = this.$root.originalFields.find(of => of.id === this.field.id)
            const originalOption = originalField?.options?.[index]

            option.label = nextValue;
            if (!originalOption?.value) {
                option.value = slugify(nextValue);
            }
        },
        openEditMode() {
            // If it's a core field dont allow editing
            if (this.field.core) return

            this.editingMode = true
        },
        createOptionId() {
            const optionIdList = this.dropdownOptionsProxy
                .map(option => Number(option.id))
                .filter(id => !isNaN(id)); // remove NaN values

            const maxId = optionIdList.length > 0 ? Math.max(...optionIdList) : 0;
            return maxId + 1;
        }
    },
    watch: {
        'field.title'(nextTitle) {
            const originalField = this.$root.originalFields.find(of => of.id === this.field.id)
            if (!originalField?.name) {
                const slugTitle = slugify(nextTitle)
                this.field.name = slugTitle
            }
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
                        <span class="text-caption">{{ translations.width_ }}</span>:
                        <v-btn-toggle v-model="widthProxy" :disabled="field.core" color="primary" mandatory density="compact" variant="outlined" divided rounded>
                            <v-btn value="w-100">
                                {{ translations.full_ }}
                            </v-btn>
                            <v-btn value="w-50">
                                {{ translations.half_ }}
                            </v-btn>
                        </v-btn-toggle>
                    </div>

                    <v-icon class="drag-handle cursor-grab" size="large">mdi-drag-horizontal</v-icon>

                    <div class="d-flex ga-4">
                        <v-tooltip location="top">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" :disabled="field.core" @click="field.required = !field.required" density="comfortable" :color="field.required ? 'primary' : null" variant="flat" icon size="small"><v-icon>mdi-asterisk</v-icon></v-btn>
                            </template>
                            {{ translations.markFieldAsRequired_ }}
                        </v-tooltip>
                        <v-tooltip location="top">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" :disabled="field.core" @click="field.searchable = !field.searchable" density="comfortable" :color="field.searchable ? 'primary' : null" variant="flat" icon size="small"><v-icon>mdi-magnify</v-icon></v-btn>
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

                <div v-if="!editingMode" :class="{'cursor-pointer': !dragging }" @click="openEditMode">
                    <div class="pointer-events-none">
                        <component :is="componentProps.component" v-bind="componentProps">
                            <template #append-inner>
                                <v-chip v-if="field.core" variant="outlined" color="purple-lighten-1" class="rounded">
                                    {{ translations.default_ }}
                                </v-chip>
                                <v-chip v-else variant="outlined" class="rounded">
                                    {{ translations.custom_ }}
                                </v-chip>
                            </template>
                        </component>
                    </div>
                </div>
                <div v-else>
                    <v-text-field variant="filled" :label="translations.fieldLabel_" v-model="field.title"></v-text-field>

                    <div class="d-flex flex-wrap ga-4">
                        <div
                            v-if="field.ui_component === 'dropdown' || field.ui_component === 'multi_dropdown'"
                            class="w-100 w-md-50"
                            style="flex: 1 1 calc(50% - 16px)"
                        >
                            <div class="d-flex flex-column">
                                <div class="text-subtitle-1 font-weight-medium text-primary">{{ translations.fieldOptions_ }}</div>

                                <div class="mt-2">
                                    <draggable v-model="dropdownOptionsProxy" :item-key="'id'" class="d-flex flex-column ga-1" handle=".drag-handle">
                                            <template #item="{ element: option, index }">
                                                <div class="d-flex align-center ga-2">
                                                    <v-icon class="drag-handle cursor-grab">mdi-drag</v-icon>
                                                    <div>{{ option.id || index + 1 }}</div>
                                                    <v-text-field
                                                        :label="translations.optionN_(index + 1)"
                                                        :model-value="option.label"
                                                        @update:model-value="updateDropdownOption($event, option, index)"
                                                        variant="filled"
                                                        hide-details
                                                        :disabled="option.hidden"
                                                    ></v-text-field>

                                                    <v-tooltip location="top">
                                                        <template v-slot:activator="{ props }">
                                                            <v-btn v-bind="props" :icon="option.hidden ? 'mdi-eye-outline' : 'mdi-eye-off-outline'" density="comfortable" variant="text" @click="option.hidden = !option?.hidden"></v-btn>
                                                        </template>
                                                        {{ option.hidden ? translations.showOption_ : translations.hideOption_ }}
                                                    </v-tooltip>
                                                </div>
                                            </template>
                                    </draggable>


                                    <v-btn class="mt-4" @click="dropdownOptionsProxy.push({ id: createOptionId(), label: '', value: '', hidden: false })" prepend-icon="mdi-plus-circle" color="primary" variant="text">{{ translations.addAnotherOption_ }}</v-btn>
                                </div>

                            </div>
                        </div>

                        <div class="w-100 w-md-50" style="flex: 1 1 calc(50% - 16px)">
                            <div class="text-subtitle-1 font-weight-medium text-primary">{{ translations.fieldProperties_ }}</div>
                            <div class="mt-2 ga-4" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));">
                                <v-text-field
                                    variant="filled"
                                    :label="translations.helpText_"
                                    v-model="field.ui_config.help_text"
                                ></v-text-field>
                                <v-text-field
                                    v-if="field.ui_component === 'input'"
                                    variant="filled"
                                    :label="translations.maxLength_"
                                    v-model="field.validation_config.max_length"
                                ></v-text-field>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </template>
    </v-hover>

    <div v-else>{{ translations.noUiComponentMappedForThisField_ }}</div>
    `,
});
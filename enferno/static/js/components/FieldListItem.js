const iconMap = {
    input: 'mdi-text-short',
    textarea: 'mdi-text-long', 
    dropdown: 'mdi-chevron-down-circle-outline',
    number_input: 'mdi-numeric',
    date_picker: 'mdi-calendar-blank-outline',
    multi_dropdown: 'mdi-format-list-checks',
    html_block: 'mdi-code-tags',  // Icon for HTML block components
}

const FieldListItem = Vue.defineComponent({
    props: {
        field: {
            type: Object,
            default: () => ({})
        },
        dragging: {
            type: Boolean,
            default: false,
        },
        hideDragHandle: {
            type: Boolean,
            default: false
        }
    },
    emits: ['delete', 'toggle-visibility', 'width'],
    data() {
        return {
            translations: window.translations,
            editingMode: false,
            nonHideableFields: ['title', 'comments', 'status']
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
                return (this.field?.ui_component === 'dropdown')
                    ? this.field?.options || [{ id: 1, label: this.translations.optionN_(1), hidden: false }]
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
                bgColor: !this.$vuetify.theme.global.current.dark && field.core ? 'core-field-accent' : undefined,
                class: 'h-100'
            };

            const numberProps = {
                precision: field.field_type === 'float'
                    ? Number(field?.validation_config?.precision) || null
                    : 0,
                min: field?.validation_config?.min,
                max: field?.validation_config?.max,
                controlVariant: 'hidden'
            };

            const componentMap = {
                input: { component: 'v-text-field', ...baseProps },
                textarea: { component: 'v-textarea', ...baseProps },
                number_input: { component: 'v-text-field', ...baseProps, ...numberProps },
                dropdown: {
                    component: 'v-select',
                    ...baseProps,
                    items: field.options || [],
                    'item-title': 'label',
                    'item-value': 'id',
                    multiple: field.schema_config?.allow_multiple || false
                },
                date_picker: { component: 'v-text-field', ...baseProps },
                html_block: { 
                    component: 'v-text-field', 
                    ...baseProps,
                    readonly: true
                },
            };

            return componentMap[field.ui_component] || null;
        },
        updateDropdownOption(nextValue, option) {
            option.label = nextValue;
        },
        openEditMode() {
            // If it's a core field dont allow editing
            if (this.field.core) return

            this.editingMode = true
        },
        createOptionId() {
            // Create option id by finding the largest number + 1
            const optionIdList = this.dropdownOptionsProxy
                .map(option => Number(option.id))
                .filter(id => !isNaN(id)); // remove NaN values

            const maxId = optionIdList.length > 0 ? Math.max(...optionIdList) : 0;
            return maxId + 1;
        },
        addDropdownOption() {
            const nextNumber = this.dropdownOptionsProxy.length + 1
            this.dropdownOptionsProxy.push({
                id: this.createOptionId(),
                label: this.translations.optionN_(nextNumber),
                hidden: false
            });
            this.$nextTick(() => {
                this.$refs.optionsRef.$el.scrollTo({
                    top: this.$refs.optionsRef.$el.scrollHeight,
                    behavior: 'smooth'
                });
            })
        },
        toggleAllowMultiple(nextValue) {
            // Initialize schema_config if it doesn't exist
            if (!this.field.schema_config) {
                this.field.schema_config = {};
            }
            // Toggle the allow_multiple property
            this.field.schema_config.allow_multiple = !nextValue;
        }
    },
    template: `
    <v-hover v-if="componentProps">
        <template v-slot:default="{ isHovering, props }">
            <div v-bind="props" v-click-outside="() => this.editingMode = false" class="d-flex flex-column ga-1 px-6 pb-6 position-relative rounded-16 overflow-hidden h-100">
                <v-slide-x-transition>
                    <div v-if="editingMode" class="position-absolute top-0 left-0 h-100 bg-primary" style="width: 10px;"></div>
                </v-slide-x-transition>

                <div :class="['d-flex justify-space-between align-center opacity-0', { 'opacity-100': editingMode || (isHovering && !dragging), 'pointer-events-none': dragging }]">
                    <div>
                        <span class="text-caption">{{ translations.width_ }}</span>:
                        <v-btn-toggle v-model="widthProxy" rounded="pill" :disabled="field.core" color="primary" mandatory density="compact" variant="outlined" divided>
                            <v-btn value="w-100">
                                {{ translations.full_ }}
                            </v-btn>
                            <v-btn value="w-50">
                                {{ translations.half_ }}
                            </v-btn>
                        </v-btn-toggle>
                    </div>

                    <v-icon v-if="!hideDragHandle" class="drag-handle cursor-grab" size="large">mdi-drag-horizontal</v-icon>

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
                                <v-btn v-bind="props" :disabled="nonHideableFields.includes(field.name)" density="comfortable" variant="flat" icon @click="$emit('toggle-visibility', { field, componentProps })" size="small"><v-icon>{{ componentProps.disabled ? 'mdi-eye-outline' : 'mdi-eye-off-outline' }}</v-icon></v-btn>
                            </template>
                            {{ field.active ? translations.hideField_ : translations.showField_ }}
                        </v-tooltip>
                        <v-tooltip location="top">
                            <template v-slot:activator="{ props }">
                                <span v-bind="props">
                                    <v-btn density="comfortable" variant="flat" :disabled="field.core || !field.active" icon @click="$emit('delete', { field, componentProps })" size="small"><v-icon>mdi-trash-can-outline</v-icon></v-btn>
                                </span>
                            </template>
                            {{ field.core ? translations.deletionRestricted_ : translations.deleteField_ }}
                        </v-tooltip>
                    </div>
                </div>

                <div v-if="!editingMode" :class="['h-100', {'cursor-pointer': !dragging }]" @click="openEditMode">
                    <div class="h-100 pointer-events-none">
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
                    <v-text-field variant="filled" :label="translations.fieldLabel_" v-model="field.title" autofocus clearable></v-text-field>

                    <div class="d-flex flex-wrap ga-4">
                        <div
                            v-if="field.ui_component === 'dropdown'"
                            class="w-100 w-md-50"
                            style="flex: 1 1 calc(50% - 16px)"
                        >
                            <div class="d-flex flex-column">
                                <div class="d-flex justify-space-between align-center">
                                    <div class="text-subtitle-1 font-weight-medium text-primary">{{ translations.fieldOptions_ }}</div>

                                    <v-checkbox class="text-medium-emphasis" :label="translations.oneSelectionOnly_" hide-details :model-value="!Boolean(field?.schema_config?.allow_multiple)" @update:model-value="toggleAllowMultiple"></v-checkbox>
                                </div>

                                <div class="mt-2">
                                    <draggable ref="optionsRef" v-model="dropdownOptionsProxy" :item-key="'id'" class="d-flex flex-column ga-1 overflow-y-auto" handle=".drag-handle" style="max-height: 260px;">
                                        <template #item="{ element: option, index }">
                                            <div class="d-flex align-center ga-2">
                                                <v-icon class="drag-handle cursor-grab">mdi-drag</v-icon>
                                                <div>{{ option.id || index + 1 }}</div>
                                                <v-text-field
                                                    :label="translations.optionN_(index + 1)"
                                                    :model-value="option.label"
                                                    @update:model-value="updateDropdownOption($event, option)"
                                                    variant="filled"
                                                    hide-details
                                                    :disabled="option.hidden"
                                                    clearable
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


                                    <v-btn class="mt-4" @click="addDropdownOption()" prepend-icon="mdi-plus-circle" color="primary" variant="text">{{ translations.addAnotherOption_ }}</v-btn>
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
                                    clearable
                                ></v-text-field>
                                <v-number-input
                                    v-if="field.ui_component === 'input'"
                                    variant="filled"
                                    :label="translations.maxLength_"
                                    v-model="field.validation_config.max_length"
                                    clearable
                                    control-variant="hidden"
                                    :max="255"
                                ></v-number-input>
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

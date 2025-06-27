const IdNumberDynamicField = Vue.defineComponent({
    props: {
      modelValue: {
        type: Array,
        required: true,
        default: () => []
      },
      idNumberTypes: {
        type: Array,
        required: true,
        default: () => []
      },
    },
    emits: ['update:modelValue'],
    data: () => {
      return {
        translations: window.translations,
        validationRules: validationRules,
      };
    },
    methods: {
        addIdNumber() {
          const current = Array.isArray(this.modelValue) ? this.modelValue : [];
          this.$emit('update:modelValue', [...current, { type: null, number: null, id: generateRandomId() }]);
        },
      
        removeIdNumber(index) {
            const current = Array.isArray(this.modelValue) ? this.modelValue : [];
            if (index < 0 || index >= current.length) return;
          
            const record = current[index];
            const hasData = Boolean(record?.type || record?.number);
          
             // Only ask confirmation if the record has data
            if (hasData && !confirm(translations.areYouSureYouWantToDeleteThisRecord_)) {
              return;
            }
          
            const updated = [...current];
            updated.splice(index, 1);
            this.$emit('update:modelValue', updated);
        },
          
      
        updateIdNumber(index, field, value) {
          const current = Array.isArray(this.modelValue) ? this.modelValue : [];
          if (index < 0 || index >= current.length) return;
          if (field !== 'type' && field !== 'number') return;
      
          const updated = [...current];
          const updatedItem = { ...updated[index] };
      
          if (typeof value === 'string') {
            updatedItem[field] = field === 'type' ? value.toString() : value.trim();
          } else {
            updatedItem[field] = value;
          }
      
          updated.splice(index, 1, updatedItem);
          this.$emit('update:modelValue', updated);
        },
    },
    template: `
        <v-card>
            <v-card-item>
                <v-card-title>{{ translations.idNumber_ }}</v-card-title>
            </v-card-item>
            
            <!-- Display and edit existing ID numbers -->
            <v-card-text class="pb-0">
                <div v-for="(idEntry, index) in modelValue" :key="idEntry.id" class="d-flex align-center ga-4 mb-2">
                    <v-select
                        :model-value="idEntry.type"
                        :items="idNumberTypes"
                        item-title="title"
                        item-value="id"
                        :label="translations.idType_"
                        class="w-100"
                        @update:model-value="updateIdNumber(index, 'type', $event)"
                        :rules="idEntry.type || idEntry.number ? [validationRules.required()] : []"
                    ></v-select>
                    
                    <v-text-field
                        v-model="idEntry.number"
                        :label="translations.number_"
                        class="w-100"
                        @update:model-value="updateIdNumber(index, 'number', $event)"
                        @keydown.enter="$event.target.blur()"
                        :rules="idEntry.type || idEntry.number ? [validationRules.required()] : []"
                    ></v-text-field>
                    
                    <v-btn
                        v-if="(modelValue?.length || 0) > 1"
                        @click="removeIdNumber(index)"
                        icon="mdi-delete"
                        color="red"
                        variant="text"
                        class="mb-5"
                    ></v-btn>
                </div>
            </v-card-text>

            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn
                    @click="addIdNumber"
                    prepend-icon="mdi-plus"
                    color="primary"
                    variant="flat"
                >Add new row</v-btn>
            </v-card-actions>
        </v-card>
    `,
  });
  
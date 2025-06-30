const IdNumberDynamicField = Vue.defineComponent({
    props: {
      modelValue: {
        type: Array,
        required: true,
        default: () => [{ type: null, number: null }]
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
        generateRandomId() {
          const timestamp = Date.now().toString(36);
          const random = Math.random().toString(36).slice(2, 7);

          return `${timestamp}-${random}`;
        },

        addIdNumber() {
          const current = Array.isArray(this.modelValue) ? this.modelValue : [];
          this.$emit('update:modelValue', [...current, { type: null, number: null, id: this.generateRandomId() }]);
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

        normalizeIds(list) {
          const updated = list.map(item => ({
            ...item,
            id: item.id || this.generateRandomId()
          }));
        
          const needsUpdate = updated.some((item, i) => item.id !== list[i].id);
          if (needsUpdate) {
            this.$emit('update:modelValue', updated);
            return true;
          }
        
          return false;
        }
    },
    watch: {
        modelValue: {
            immediate: true,
            handler(newVal) {
              if (!Array.isArray(newVal) || newVal.length === 0) {
                this.$emit('update:modelValue', [{ type: null, number: null, id: this.generateRandomId() }]);
                return;
              }

              this.normalizeIds(newVal);
            }
        }
    },      
    template: /*html*/`
        <v-card>
            <v-toolbar>
                <v-toolbar-title>{{ translations.idNumbers_ }}</v-toolbar-title>
                <v-spacer></v-spacer>
                <v-btn
                  @click="addIdNumber()"
                  color="primary"
                  icon="mdi-plus-circle"
                ></v-btn>
            </v-toolbar>
            
            <!-- Display and edit existing ID numbers -->
            <v-card-text class="pb-0">
                <div v-for="(idEntry, index) in modelValue" :key="idEntry.id" class="d-flex align-center ga-4 mb-2">
                    <v-select
                        :model-value="Number(idEntry.type) || null"
                        :items="idNumberTypes"
                        item-title="title"
                        item-value="id"
                        :label="translations.idType_"
                        class="w-100"
                        @update:model-value="updateIdNumber(index, 'type', $event)"
                        :rules="idEntry.type || idEntry.number ? [validationRules.required()] : []"
                    ></v-select>
                    
                    <v-text-field
                        :model-value="idEntry.number"
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
        </v-card>
    `,
  });
  
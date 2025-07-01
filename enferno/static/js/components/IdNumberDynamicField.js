const IdNumberDynamicField = Vue.defineComponent({
    props: {
      modelValue: {
        type: Array,
        required: true,
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
        items: [{ type: null, number: null }],
      };
    },
    mounted() {
      if (Array.isArray(this.modelValue) && this.modelValue.length > 0) {
        this.items = this.modelValue
      }
    },
    methods: {
        emitAndFilterEmptyItems() {
          const filteredItems = this.items.filter(item => item.type && item.number);
          this.$emit('update:modelValue', filteredItems);
        },
        addIdNumber() {
          this.items.push({ type: null, number: null });
          this.emitAndFilterEmptyItems();
        },
        removeIdNumber(index) {
            const record = this.items[index];
            const hasData = Boolean(record?.type || record?.number);
          
             // Only ask confirmation if the record has data
            if (!hasData || confirm(translations.areYouSureYouWantToDeleteThisRecord_)) {
              this.items.splice(index, 1);
              this.emitAndFilterEmptyItems();
            }
        },
        updateIdNumber(index, field, value) {
          if (this.items?.[index]?.[field] === undefined) return;

          this.items[index][field] = value;
          this.emitAndFilterEmptyItems();
        },        
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
                <div v-for="(idEntry, index) in items" :key="index" class="d-flex align-center ga-4 mb-2">
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
                        v-if="(items?.length || 0) > 1"
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
  
const getEmptyIdEntry = () => ({ id: Date.now(), type: null, number: null });

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
    data: () => ({
      translations: window.translations,
      validationRules: validationRules,
      items: [getEmptyIdEntry()]
    }),
    
    methods: {
      emitAndFilterEmptyItems() {
        const filtered = this.items.filter(i => i.type && i.number);
        this.$emit('update:modelValue', filtered);
      },
      addIdNumber() {
        this.items.push(getEmptyIdEntry());
        this.emitAndFilterEmptyItems();
      },
      removeIdNumber(index) {
        const record = this.items[index];
        const hasData = Boolean(record?.type || record?.number);
    
        if (!hasData || confirm(this.translations.areYouSureYouWantToDeleteThisRecord_)) {
          if (this.items.length === 1) {
            this.items.splice(index, 1, getEmptyIdEntry());
          } else {
            this.items.splice(index, 1);
          }
          this.emitAndFilterEmptyItems();
        }
      },
      updateIdNumber(index, field, value) {
        if (!this.items[index]) return;
        this.items[index][field] = value;
        this.emitAndFilterEmptyItems();
      }
    },
    watch: {
      modelValue: {
        immediate: true,
        handler(newVal) {
          if (this.hasOnlyEmptyRow && Array.isArray(newVal) && newVal.length > 0) {
            this.items = [...newVal];
          }
        }
      }
    },
    computed: {
      hasOnlyEmptyRow() {
        const [row] = this.items;
        return this.items.length === 1 && row?.type === null && row?.number === null;
      },
      isDirty() {
        return Boolean(this.items?.some(item => item?.type !== null || item?.number !== null))
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
                <div v-for="(idEntry, index) in items" :key="idEntry.id ?? index" class="d-flex align-center ga-4 mb-2">
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
                        v-if="isDirty"
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
  
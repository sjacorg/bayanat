const EditableTable = Vue.defineComponent({
  props: {
    loadEndpoint: {
      type: String,
      required: true,
    },
    saveEndpoint: {
      type: String,
      required: true,
    },
    deleteEndpoint: {
      type: String,
      required: false,
      default: null,
    },
    itemHeaders: {
      type: Array,
      required: true,
    },
    height: {
      type: String,
      default: null,
    },
    title: {
      type: String,
      default: 'Editable Table',
    },
    addButtonLabel: {
      type: String,
      default: 'Add new',
    },
    allowAdd: {
      type: Boolean,
      default: true,
    },
    noActionIds: {
      type: Array,
      default: () => [], // Default to an empty array
    },
    noDeleteActionIds: {
      type: Array,
      default: () => [],
    },
    noEditActionIds: {
      type: Array,
      default: () => [],
    },
    editableColumns: {
      type: Array,
      default: () => ['title'],
    },
    requiredFields: {
      type: Array,
      default: () => [],
    },
    columnsList: {
      type: Array,
      default: () => ['code', 'title', 'title_tr', 'reverse_title', 'reverse_title_tr'],
    },
  },
  template: `
      <div>
        <v-data-table :loading="isLoadingList || dialogState.isLoading" fixed-header fixed-footer :height="height" :headers="itemHeaders" :items="itemList" :items-per-page-options="$root.itemsPerPageOptions">
        
          <template v-slot:top>
            <v-toolbar class="d-flex justify-space-between align-center" color="white">
              <v-toolbar-title class="text-subtitle-1">{{ title }}</v-toolbar-title>

              <v-btn class="mx-3" v-if="allowAdd" prepend-icon="mdi-plus-circle" @click="itemAdd()" variant="elevated" color="primary">{{ addButtonLabel }}</v-btn>
            </v-toolbar>
          </template>

          <template v-for="column in columnsList" v-slot:[\`item.\${column}\`]="{ item }">
            <span>{{ item[column] }}</span>
          </template>

          <template v-slot:item.actions="{ item }">
            <div class="d-inline-flex ga-1" v-if="isActionable(item)">
              <v-btn v-if="isEditable(item)" variant="plain" size="small" @click="itemEdit(item)" icon="mdi-pencil"></v-btn>
              <v-btn v-if="deleteEndpoint && isDeletable(item)" variant="plain" size="small" @click="itemDelete(item)" icon="mdi-delete-sweep"></v-btn>
            </div>
          </template>
        </v-data-table>

        <v-dialog v-model="dialogState.isOpen" max-width="900px">
          <v-card :title="dialogTitles[dialogState.mode]">
            <v-form ref="form" @submit.prevent="itemSave">
              <v-card-text>
                  <v-container>
                      <v-row>
                        <template v-for="(column, index) in columnsList">
                          <v-col v-if="isEditable(dialogState.item) && editableColumns.includes(column)" cols="12" md="6">
                            <v-text-field
                              variant="outlined"
                              v-model="dialogState.item[column]"
                              :autofocus="index === 0"
                              :rules="isRequired(column) ? [validationRules.required()] : []"
                            >
                              <template v-slot:label>
                                {{ getHeaderTextById(column) }} <Asterisk v-if="isRequired(column)" />
                              </template>
                            </v-text-field>
                          </v-col>
                        </template>
                      </v-row>
                  </v-container>
              </v-card-text>

              <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn
                    @click="dialogState.isOpen = false"
                  >Cancel</v-btn>
                  <v-btn
                    :loading="dialogState.isLoading"
                    color="primary"
                    type="submit"
                    variant="elevated"
                  >Save</v-btn
                  >
              </v-card-actions>
            </v-form>
          </v-card>
      </v-dialog>
      </div>
    `,
  data: function () {
    return {
      itemList: [],
      editableItem: {},
      translations: window.translations,
      validationRules: validationRules,
      isLoadingList: false,
      dialogState: {
        isLoading: false,
        isOpen: false,
        mode: 'insert',
        item: null
      },
    };
  },
  emits: ['items-updated'],
  mounted() {

    this.loadItems();
  },
  computed: {
    dialogTitles() {
      return {
        insert: this.translations.newItem_,
        update: `${this.translations.editItem_} ${this.dialogState.item?.id ?? ''}`,
      }
    }
  },
  methods: {
    loadItems() {
      this.isLoadingList = true;
      axios
        .get(this.loadEndpoint)
        .then((res) => {
          this.itemList = res.data.items;
          this.$emit('items-updated', this.itemList);
        })
        .catch((e) => {
          console.log(e.response.data);
        })
        .finally(() => {
          this.isLoadingList = false;
        });
    },

    itemEdit(item) {
      this.dialogState = {
        isLoading: false,
        isOpen: true,
        mode: 'update',
        item: JSON.parse(JSON.stringify(item)),
      };
    },

    itemSave() {
      this.$refs.form.validate().then(({ valid }) => {
        if (!valid) {
          this.$root.showSnack(this.translations.pleaseReviewFormForErrors_);
          return;
        }

        this.dialogState.isLoading = true;
        const endpoint = this.dialogState.item?.id ? `${this.saveEndpoint}/${this.dialogState.item.id}` : this.saveEndpoint;
        const method = this.dialogState.item?.id ? 'put' : 'post';

        // fix for location admin levels
        if(this.itemHeaders.find(header => header.value === 'code') && !this.dialogState.item?.id){
          const maxCode = this.itemList.reduce((acc, item) => acc > item.code ? acc : item.code, 0);
          this.dialogState.item.code = Number(maxCode) + 1;
        }

        axios[method](endpoint, { item: this.dialogState.item })
          .then((res) => {
            this.loadItems();
            this.$root.showSnack(res.data);
            this.$emit('items-updated', this.itemList);
            this.dialogState.isOpen = false;
            // Only clear on success
            this.dialogState.item = {};
          })
          .catch((err) => {
            // Show error but keep dialog open and data intact
            this.$root.showSnack(err.response?.data?.message || this.translations.errorOccurred_ || 'An error occurred');
          })
          .finally(() => {
            this.dialogState.isLoading = false;
          });
      });
    },

    itemCancel() {
      this.dialogState.item = {};
    },

    itemAdd() {
      this.dialogState = {
        isLoading: false,
        isOpen: true,
        mode: 'insert',
        item: {}
      }
    },

    itemDelete(item) {
      if (confirm(`${this.translations.confirmDelete_}: "${item.title}"`)) {
        axios
          .delete(`${this.deleteEndpoint}/${item.id}`)
          .then((res) => {
            this.loadItems();
            this.$root.showSnack(res.data);
            this.$emit('items-updated', this.itemList);
          });
      }
    },
    getHeaderTextById(column) {
      return this.itemHeaders?.find((header) => header?.value === column)?.title
    },
    isActionable(item) {
      return !this.noActionIds.includes(item?.id);
    },
    isDeletable(item) {
      return !this.noDeleteActionIds.includes(item?.id);
    },
    isEditable(item) {
      return !this.noEditActionIds.includes(item?.id);
    },
    isRequired(column) {
      return this.requiredFields.includes(column);
    },
  },
});
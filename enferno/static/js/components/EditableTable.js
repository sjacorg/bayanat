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
  },
  template: `
      <div>
        <v-data-table :headers="itemHeaders" :items="itemList" :items-per-page-options="$root.itemsPerPageOptions">
        
          <template v-slot:top>
            <v-toolbar class="d-flex justify-space-between align-center" color="white">
              <v-toolbar-title class="text-subtitle-1">{{ title }}</v-toolbar-title>

              <v-btn class="mx-3" v-if="allowAdd" prepend-icon="mdi-plus-circle" @click="itemAdd" variant="elevated" color="primary">{{ addButtonLabel }}</v-btn>
            </v-toolbar>
          </template>

          <template v-for="column in ['title', 'title_tr', 'reverse_title_tr', 'reverse_title', 'code']" v-slot:[\`item.\${column}\`]="{ item }">
            <v-text-field
              v-if="isEditable(item) && item.id === editableItem.id && editableColumns.includes(column)"
              v-model="editableItem[column]"
              :hide-details="true"
              density="compact"
              single-line
              :autofocus="column === 'title'"
            ></v-text-field>
            <span v-else>{{ item[column] }}</span>
          </template>

          <template v-slot:item.actions="{ item }">
            <div class="d-inline-flex ga-6" v-if="isActionable(item)">
              <template v-if="item.id === editableItem.id">
                <v-icon size="large" @click="itemCancel">mdi-window-close</v-icon>
                <v-icon size="large" @click="itemSave(item)">mdi-content-save</v-icon>
              </template>
              <template v-else>
              <v-icon v-if="deleteEndpoint && isDeletable(item)" size="large" @click="itemDelete(item)">mdi-delete</v-icon>
              <v-icon v-if="isEditable(item)" size="large" @click="itemEdit(item)">mdi-pencil</v-icon>
              </template>
            </div>
          </template>
        </v-data-table>
      </div>
    `,
  data: function () {
    return {
      itemList: [],
      editableItem: {},
      translations: window.translations,
    };
  },
  emits: ['items-updated'],
  mounted() {

    this.loadItems();
  },
  mixins: [globalMixin],
  methods: {
    loadItems() {
      axios
        .get(this.loadEndpoint)
        .then((res) => {
          this.itemList = res.data.items;
          this.$emit('items-updated', this.itemList);
        })
        .catch((e) => {
          console.log(e.response.data);
        });
    },

    itemEdit(item) {
      this.editableItem = JSON.parse(JSON.stringify(item));
    },

    itemSave(item) {
      const endpoint = item.id ? `${this.saveEndpoint}/${item.id}` : this.saveEndpoint;
      const method = item.id ? 'put' : 'post';

      // fix for location admin levels
      if(this.itemHeaders.find(header => header.value === 'code') && !item.id){
        const maxCode = this.itemList.reduce((acc, item) => acc > item.code ? acc : item.code, 0);
        this.editableItem.code = Number(maxCode) + 1;
      }

      axios[method](endpoint, { item: this.editableItem })
        .then((res) => {
          this.loadItems();
          this.$root.showSnack(res.data);
          this.$emit('items-updated', this.itemList);
        })
        .finally(() => {
          this.editableItem = {};
        });
    },

    itemCancel() {
      this.editableItem = {};
    },

    itemAdd() {
      this.itemList.unshift({});
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
    isActionable(item) {
      return !this.noActionIds.includes(item.id);
    },
    isDeletable(item) {
      return !this.noDeleteActionIds.includes(item.id);
    },
    isEditable(item) {
      return !this.noEditActionIds.includes(item.id);
    },
  },
});

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
    allowAdd: {
      type: Boolean,
      default: true,
    },
    noActionIds: {
      type: Array,
      default: () => [], // Default to an empty array
    },
    editableColumns: {
      type: Array,
      default: () => ['title'],
    },
  },
  template: `
      <div>
        <v-data-table :headers="itemHeaders" :items="itemList" :items-per-page-options="$root.itemsPerPageOptions" class="elevation-1">
        
          <template v-slot:top>
            <v-toolbar :title="title" class="d-flex justify-space-between align-center" color="white">

              <v-btn icon="mdi-plus" v-if="allowAdd" @click="itemAdd" class="mx-3" variant="elevated" color="primary" size="x-small" >
              </v-btn>
            </v-toolbar>
          </template>

          <template v-slot:item.title="{ item }">
            <v-text-field v-model="editableItem.title" :hide-details="true"
                          density="compact" single-line :autofocus="true"
                          v-if="item.id === editableItem.id && editableColumns.includes('title')"></v-text-field>
            <span v-else>{{ item.title }}</span>
          </template>

          <template v-slot:item.title_tr="{ item }">
            <v-text-field v-model="editableItem.title_tr" :hide-details="true"
                          density="compact" single-line
                          v-if="item.id === editableItem.id && editableColumns.includes('title_tr')"></v-text-field>
            <span v-else>{{ item.title_tr }}</span>
          </template>

          <template v-slot:item.reverse_title_tr="{ item }">
            <v-text-field v-model="editableItem.reverse_title_tr" :hide-details="true"
                          density="compact" single-line
                          v-if="item.id === editableItem.id && editableColumns.includes('reverse_title_tr')"></v-text-field>
            <span v-else>{{ item.reverse_title_tr }}</span>
          </template>


          <template v-slot:item.reverse_title="{ item }">
            <v-text-field v-model="editableItem.reverse_title" :hide-details="true"
                          density="compact" single-line
                          v-if="item.id === editableItem.id && editableColumns.includes('reverse_title')"></v-text-field>
            <span v-else>{{ item.reverse_title }}</span>
          </template>


          <template v-slot:item.actions="{ item }">
            <div v-if="!noActionIds.includes(item.id)">

              <div v-if="item.id === editableItem.id">
                <v-icon size="small" class="mr-3" @click="itemCancel">
                  mdi-window-close
                </v-icon>
                <v-icon size="small" @click="itemSave(item)">mdi-content-save
                </v-icon>
              </div>
              <div v-else>
                <v-icon size="small" class="mr-3" @click="itemEdit(item)">
                  mdi-pencil
                </v-icon>
                <v-icon v-if="deleteEndpoint" size="small" @click="itemDelete(item)">mdi-delete
                </v-icon>

              </div>
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
  mounted() {

    this.loadItems();
  },
  methods: {
    loadItems() {
      axios
        .get(this.loadEndpoint)
        .then((res) => {
          this.itemList = res.data.items;
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

      axios[method](endpoint, { item: this.editableItem })
        .then((res) => {
          this.loadItems();
          this.showSnack(res.data);
        })
        .catch((err) => {
          this.showSnack(this.parseValidationError(err.response.data));
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
      if (confirm(`${translations.confirmDelete_}: "${item.title}"`)) {
        axios
          .delete(`${this.deleteEndpoint}/${item.id}`)
          .then((res) => {
            this.loadItems();
            this.showSnack(res.data);
          })
          .catch((err) => {
            console.log(err.response.data);
            this.showSnack(this.parseValidationError(err.response.data));
          });
      }
    },
  },
});

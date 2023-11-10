Vue.component("EditableTable", {
    props: {
        loadEndpoint: {
            type: String,
            required: true
        },
        saveEndpoint: {
            type: String,
            required: true
        },
        deleteEndpoint: {
            type: String,
            required: false,
            default: null
        },
        itemHeaders: {
            type: Array,
            required: true
        },
        title: {
            type: String,
            default: 'Editable Table'
        },
        allowAdd: {
            type: Boolean,
            default: true
        },
        noActionIds: {
            type: Array,
            default: () => []  // Default to an empty array
        },
        editableColumns: {
            type: Array,
            default: () => ['title'],
        }
    },
    template: `
      <div>
        <v-card-title>
          {{ title }}
          <v-spacer></v-spacer>
          <v-btn v-if="allowAdd" @click="itemAdd" class="mx-3" elevation="0" color="primary" fab x-small>
            <v-icon>mdi-plus</v-icon>
          </v-btn>
        </v-card-title>
        <v-data-table :headers="itemHeaders" :items="itemList" class="elevation-1">
          <template v-slot:item.title="{ item }">
            <v-text-field v-model="editableItem.title" :hide-details="true"
                          dense single-line :autofocus="true"
                          v-if="item.id === editableItem.id && editableColumns.includes('title')"></v-text-field>
            <span v-else>{{ item.title }}</span>
          </template>

          <template v-slot:item.title_tr="{ item }">
            <v-text-field v-model="editableItem.title_tr" :hide-details="true"
                          dense single-line
                          v-if="item.id === editableItem.id && editableColumns.includes('title_tr')"></v-text-field>
            <span v-else>{{ item.title_tr }}</span>
          </template>

          <template v-slot:item.reverse_title_tr="{ item }">
            <v-text-field v-model="editableItem.reverse_title_tr" :hide-details="true"
                          dense single-line
                          v-if="item.id === editableItem.id && editableColumns.includes('reverse_title_tr')"></v-text-field>
            <span v-else>{{ item.reverse_title_tr }}</span>
          </template>


          <template v-slot:item.reverse_title="{ item }">
            <v-text-field v-model="editableItem.reverse_title" :hide-details="true"
                          dense single-line
                          v-if="item.id === editableItem.id && editableColumns.includes('reverse_title')"></v-text-field>
            <span v-else>{{ item.reverse_title }}</span>
          </template>


          <template v-slot:item.actions="{ item }">
            <div v-if="!noActionIds.includes(item.id)">

              <div v-if="item.id === editableItem.id">
                <v-icon small class="mr-3" @click="itemCancel">
                  mdi-window-close
                </v-icon>
                <v-icon small @click="itemSave(item)">mdi-content-save
                </v-icon>
              </div>
              <div v-else>
                <v-icon small class="mr-3" @click="itemEdit(item)">
                  mdi-pencil
                </v-icon>
                <v-icon v-if="deleteEndpoint" small @click="itemDelete(item)">mdi-delete
                </v-icon>

              </div>
            </div>
          </template>
        </v-data-table>
        <v-snackbar v-model="snackbar" class="d-flex">
          {{ snackMessage }}
          <v-btn color="grey lighten-4" text @click.stop="snackbar = false">
            Close
          </v-btn>
        </v-snackbar>
      </div>
    `,
    data: function () {
        return {
            itemList: [],
            editableItem: {},
            snackMessage: '',
            snackbar: false
        };
    },
    mounted() {
        this.loadItems();
    },
    methods: {
        loadItems() {
            axios.get(this.loadEndpoint).then(res => {
                this.itemList = res.data.items;
            }).catch(e => {
                console.log(e.response.data);
            });
        },

        itemEdit(item) {
            this.editableItem = JSON.parse(JSON.stringify(item));
        },

        itemSave(item) {

            const endpoint = item.id ? `${this.saveEndpoint}/${item.id}` : this.saveEndpoint;
            const method = item.id ? 'put' : 'post';

            axios[method](endpoint, {item: this.editableItem}).then(res => {
                this.loadItems();
                this.showSnack(res.data);
            }).catch(err => {
                this.showSnack(err.response.data);
            }).finally(() => {
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
            if (confirm(`Are you sure you want to delete: "${item.title}"`)) {
                axios.delete(`${this.deleteEndpoint}/${item.id}`).then(res => {
                    this.loadItems();
                    this.showSnack(res.data);
                }).catch(err => {
                    console.log(err.response.data);
                    this.showSnack(err.response.data);
                });
            }
        },

        showSnack(message) {
            this.snackMessage = message;
            this.snackbar = true;
        }
    }
});

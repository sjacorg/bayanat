const ImportLogCard = Vue.defineComponent({
  props: ['log'],

  mounted() {

    //convert expiry to localized date
    this.log.imported_at = this.localDate(this.log.imported_at);

    if (this.item?.id) {
      this.loadImportedItem();
    }
  },

  mixins: [globalMixin],


  methods: {
    loadImportedItem() {
      axios
        .get(`/admin/api/bulletin/${this.log.item_id}`)
        .then((res) => {
          this.item = res.data;
        })
        .catch((error) => {
          console.log(error);
        })
    },


  },

  data: function () {
    return {
      translations: window.translations,
      item: {},
    };
  },

  template: `

      <v-card class="mx-auto pa-8">
      <v-card variant="tonal" outlined class="header-fixed mx-2">
        <v-card-text>

        <v-chip prepend-icon="mdi-account-circle-outline"  size="small" class="pa-2 mx-2 my-2">
          {{log.user['name']}}
        </v-chip>

          <!-- Table chip -->
          <v-chip size="small" color="primary" class="mx-2">
            {{ log.table.toUpperCase() }}
          </v-chip>

          <!-- File format chip -->
          <v-chip v-if="log.file_format" size="small" color="primary" class="mx-2"
                  >
            {{ log.file_format.toUpperCase() }}
          </v-chip>

          <!-- Status chip -->
              <v-chip size="small" class="mx-2 my-2">
                status: 
                {{ log.status }}
              </v-chip>
        </v-card-text>

      </v-card>

      <!-- Dates fields -->
      <div class="d-flex">
        <uni-field :caption="translations.file_" :english="log.file"></uni-field>
        <uni-field :caption="translations.createdDate_" :english="localDate(log.created_at)"></uni-field>
        <uni-field :caption="translations.importDate_" :english="localDate(log.imported_at)"></uni-field>
      </div>

      <!-- Refs -->
      <v-card v-if="log?.data?.tags?.length" outlined class="ma-2 pa-2 d-flex align-center flex-grow-1"
      color="grey lighten-5">
        <div class="caption grey--text mr-2">{{ translations.ref_ }}</div>
        <v-chip x-small v-for="tag in log.data.tags" class="caption black--text mx-1">{{ tag }}</v-chip>
      </v-card>

      <!-- Imported Item -->
      <v-card outlined color="grey lighten-5" class="ma-2" v-if="item?.id">
        <v-card-text v-if="log.table == 'bulletin'">
          <div class="pa-2 header-sticky title black--text">{{ translations.bulletin_ }}</div>
          <bulletin-result class="mt-1" :bulletin="item"></bulletin-result>
        </v-card-text>
        
         <v-card-text v-if="log.table == 'actor'">
          <div class="pa-2 header-sticky title black--text">{{ translations.actor_ }}</div>
          <actor-result class="mt-1" :actor="item"></actor-result>
        </v-card-text>
        
      </v-card>
      

       <v-card class="mx-2" elevation="0">
            <v-card-title class="body-2"> {{ translations.importLog_ }} </v-card-title>
        <v-card-text>
          <div style="white-space: pre-wrap" class="actor-description" > {{ log.log }} </div>
        </v-card-text>
      </v-card>

      </v-card>
    `,
});

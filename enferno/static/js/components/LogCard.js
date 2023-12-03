Vue.component("log-card", {
    props: ["log", "i18n"],

    watch: {
        log: function (val, old) {

        },
    },


    mounted() {
        //convert expiry to localized date
        this.log.imported_at = this.localDate(this.log.imported_at, format = false);

        if(this.item?.id){
          this.loadImportedItem();
        }
    },

    methods: {

      loadImportedItem() {

            axios.get(`/admin/api/bulletin/${this.log.item_id}`).then(res => {
              this.item = res.data;
            }).catch(error => {
              console.log(error);
            }).finally(() => {

            });
        },


      localDate: function (dt, format = true) {
          if (dt === null || dt === '') {
              return '';
          }
          // Z tells it's a UTC time
          const utcDate = new Date(`${dt}Z`);
          const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

          const localDate = utcDate.toLocaleString('en-US', {timeZone: userTimezone});

          if (!format) {
              return dateFns.format(localDate, 'YYYY-MM-DDTHH:mm');
          } else {
              return localDate
          }
      }
    },

    data: function () {
        return {
            item: {}
        };
    },

    template: `

      <v-card color="grey lighten-3" class="mx-auto pa-3">
      <v-card color="grey lighten-5" outlined class="header-fixed mx-2">
        <v-card-text>

        <v-chip color="blue-grey lighten-5" label small class="pa-2 mx-2 my-2">
          <v-icon left>
              mdi-account-circle-outline
          </v-icon>
          {{log.user['name']}}
        </v-chip>

          <!-- Table chip -->
          <v-chip pill small label color="gv darken-2"
                  class="white--text">
            {{ log.table.toUpperCase() }}
          </v-chip>

          <!-- File format chip -->
          <v-chip v-if="log.file_format" pill small label color="gv darken-2"
                  class="white--text">
            {{ log.file_format.toUpperCase() }}
          </v-chip>

          <!-- Status chip -->
          <v-chip color="white lighten-3" small label class="mx-2 my-2"
          v-tippy="{ placement : 'bottom' }" content="Status">
            <v-icon left>mdi-delta</v-icon>
            {{ log.status }}
          </v-chip>
        </v-card-text>

      </v-card>

      <!-- Dates fields -->
      <div class="d-flex">
        <uni-field caption="File" :english="log.file"></uni-field>
        <uni-field caption="Created At" :english="localDate(log.created_at)"></uni-field>
        <uni-field caption="Imported At" :english="localDate(log.imported_at)"></uni-field>
      </div>

      <!-- Refs -->
      <v-card v-if="log.data.ref && log.ref.length" outlined class="ma-2 pa-2 d-flex align-center flex-grow-1"
      color="grey lighten-5">
        <div class="caption grey--text mr-2">{{ i18n.ref_ }}</div>
        <v-chip x-small v-for="r in log.ref" class="caption black--text mx-1">{{ r }}</v-chip>
      </v-card>

      <!-- Imported Item -->
      <v-card outlined color="grey lighten-5" class="ma-2" v-if="item?.id">
        <v-card-text v-if="log.table == 'bulletin'">
          <div class="pa-2 header-sticky title black--text">{{ i18n.bulletin_ }}</div>
          <bulletin-result :i18n="translations" class="mt-1" :bulletin="item"></bulletin-result>
        </v-card-text>
        
         <v-card-text v-if="log.table == 'actor'">
          <div class="pa-2 header-sticky title black--text">{{ i18n.actor_ }}</div>
          <actor-result :i18n="translations" class="mt-1" :actor="item"></actor-result>
        </v-card-text>
        
      </v-card>
      

       <v-card class="mx-2" elevation="0">
            <v-card-title class="body-2">Import Lifecycle</v-card-title>
        <v-card-text>
          <div style="white-space: pre-wrap" class="actor-description" >{{log.log}}</div>
        </v-card-text>
      </v-card>

      </v-card>
    `,
});

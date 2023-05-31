Vue.component("export-card", {
    props: ["exp", "close", "i18n", "adminMode", ""],

    watch: {
        exp: function (val, old) {

        },
    },
    filters: {
        capitalize(value) {
            if (!value) return '';
            value = value.toString();
            return value.charAt(0).toUpperCase() + value.slice(1);
        }
    },

    mounted() {

        //convert expiry to localized date
        this.exp.expires_on = this.localDate(this.exp.expires_on, format = false);

        this.loadExportItems();

    },

    methods: {

        loadExportItems() {
            const q = [
                {ids: this.exp.items}
            ];

            axios.post(`/admin/api/bulletins/?page=${this.page}&per_page=${this.per_page}`, {q: q}).then(res => {
                this.items = [...this.items, ...res.data.items];
                this.showLoadMore = this.per_page * this.page < res.data.total;
                this.page += 1;

            })

        },

        showApprove(item) {
            return (item.status === 'Pending' || item.status === 'Failed' );
        },

        showReject(item) {
            return !(item.status === 'Rejected' || item.status === 'Expired');
        },

        showChangeExpiry(item) {
            return (item.status === 'Approved');
        },

        changeExpiry() {
            this.expiryFieldDisabled = false;
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

                //console.log((dateFns.format(localDate, 'YYYY-MM-DDTHH:m')));
                return dateFns.format(localDate, 'YYYY-MM-DDTHH:mm');
            } else {
                return localDate

            }
        }
    },

    data: function () {
        return {
            expiryFieldDisabled: true,
            showLoadMore: false,
            per_page: 5,
            page: 1,
            items: []
        };
    },

    template: `

      <v-card color="grey lighten-3" class="mx-auto pa-3">
      <v-card color="grey lighten-5" outlined class="header-fixed mx-2">
        <v-card-text>

          <!-- Export ID chip -->
          <v-chip pill small label color="gv darken-2" class="white--text">
            {{ i18n.id_ }} #{{ exp.id }}
          </v-chip>

          <!-- Table chip -->
          <v-chip pill small label color="gv darken-2"
                  class="white--text">
            {{ exp.table.toUpperCase() }}
          </v-chip>

          <!-- File format chip -->
          <v-avatar size="32" color="gv darken-2" small label class="mx-2"
          v-tippy="{ placement : 'bottom' }" :content="'Export Format: ' + exp.file_format">

            <v-icon small center color="white" v-if="exp.file_format === 'json'">mdi-code-json</v-icon>
            <v-icon small center color="white" v-if="exp.file_format === 'pdf'">mdi-file-pdf-box</v-icon>
            <v-icon small center color="white" v-if="exp.file_format === 'csv'">mdi-file-delimited-outline</v-icon>

          </v-avatar>

          <!-- Media chip -->
          <v-avatar size="32" color="grey darken-3" small label class="mx-2"
          v-tippy="{ placement : 'bottom' }" :content="'Include Media: ' + exp.include_media">

            <v-icon small center color="white" v-if="exp.include_media">mdi-paperclip-check</v-icon>
            <v-icon small center color="white" v-if="!exp.include_media">mdi-paperclip-off</v-icon>

          </v-avatar>

        </v-card-text>

        <!-- Requester chip -->
        <v-chip color="white lighten-3" small label class="pa-2 mx-2 my-2" 
        v-tippy="{ placement : 'bottom' }" content="Requester">
          <v-icon left>mdi-account-circle-outline</v-icon>
          {{ exp.requester.name }}
        </v-chip>

        <!-- Approver chip -->
        <v-chip color="white lighten-3" small label class="pa-2 mx-2 my-2" v-if="exp.approver"
        v-tippy="{ placement : 'bottom' }" content="Approver">
          <v-icon left>mdi-account-circle-outline</v-icon>
          {{ exp.approver.name }}
        </v-chip>

        <!-- Status chip -->
        <v-chip color="white lighten-3" small label class="mx-2 my-2"
        v-tippy="{ placement : 'bottom' }" content="Status">
          <v-icon left>mdi-delta</v-icon>
          {{ exp.status }}
        </v-chip>

      </v-card>

      <!-- Dates fields -->
      <div class="d-flex">
        <uni-field caption="Requested On" :english="localDate(exp.created_at)"></uni-field>
        <uni-field caption="Expires On" :english="localDate(exp.expires_on)"></uni-field>
      </div>

      <!-- Admin actions cards -->
      <v-card outlined class="mx-2" color="grey lighten-5" v-if="adminMode">
        <v-card-text>
          <div class="px-1 title black--text">Admin Actions</div>

          <!-- Approve button -->
          <v-btn
              v-if="showApprove(exp)"
              :disabled="exp.complete"
              class="ml-2"
              @click.stop="$emit('approve', exp.id)"
              small
              color="primary">
            <v-icon
                left>
              mdi-check
            </v-icon>
            Approve
          </v-btn>

          <!-- Reject button -->
          <v-btn
              v-if="showReject(exp)"
              class="ml-2"
              @click.stop="$emit('reject', exp.id)"
              small
              color="error">
            <v-icon
                left>
              mdi-close
            </v-icon>
            <span v-if="exp.status=='Approved'">Expire Now</span>
            <span v-else>Reject</span>
            
          </v-btn>

          <!-- Change expiry date button -->
          <v-btn
              v-if="expiryFieldDisabled && showChangeExpiry(exp)"
              :disabled="exp.expired"
              class="ml-2"
              @click="changeExpiry"
              small
              color="primary">
            <v-icon
                left>
              mdi-calendar-edit
            </v-icon>
            Change Expiry
          </v-btn>

          <!-- Set expiry date button -->
          <v-btn
              v-if="!expiryFieldDisabled && showChangeExpiry(exp)"
              :disabled="exp.expired"
              class="ml-2"
              @click.stop="$emit('change', exp.id, exp.expires_on)"
              small
              color="primary">
            <v-icon
                left>
              mdi-calendar-edit
            </v-icon>
            Set Expiry
          </v-btn>

        </v-card-text>

        <!-- Expiry date text field -->
        <v-text-field
            v-if="!expiryFieldDisabled && showChangeExpiry(exp)"
            type="datetime-local"
            label="Export Expiry"
            v-model="exp.expires_on"
        >
        </v-text-field>

      </v-card>

      <!-- Refs -->
      <v-card v-if="exp.ref && exp.ref.length" outlined class="ma-2 pa-2 d-flex align-center flex-grow-1"
      color="grey lighten-5">
        <div class="caption grey--text mr-2">{{ i18n.ref_ }}</div>
        <v-chip x-small v-for="r in exp.ref" class="caption black--text mx-1">{{ r }}</v-chip>
      </v-card>

      <!-- Comment -->
      <uni-field :caption="i18n.comment_" :english="exp.comment"></uni-field>

      <!-- Related Bulletins -->
      <v-card outlined color="grey lighten-5" class="ma-2" v-if="items">
        <v-card-text v-if="exp.table == 'bulletin'">
          <div class="pa-2 header-sticky title black--text">{{ i18n.relatedBulletins_ }}</div>
          <bulletin-result :i18n="translations" class="mt-1" v-for="item in items" :bulletin="item"></bulletin-result>
        </v-card-text>
        
         <v-card-text v-if="exp.table == 'actor'">
          <div class="pa-2 header-sticky title black--text">{{ i18n.relatedActors_ }}</div>
          <actor-result :i18n="translations" class="mt-1" v-for="item in items" :actor="item"></actor-result>
        </v-card-text>
        
        
         <v-card-text v-if="exp.table == 'incident'">
          <div class="pa-2 header-sticky title black--text">{{ i18n.relatedIncidents_ }}</div>
          <incident-result :i18n="translations" class="mt-1" v-for="item in items" :incident="item"></incident-result>
        </v-card-text>
        
        
        <v-card-actions>
          <v-btn 
            class="ma-auto caption" 
            small 
            color="grey lighten-4" 
            elevation="0" 
            @click="loadExportItems" 
            v-if="showLoadMore"
            >Load More
              <v-icon right>mdi-chevron-down</v-icon></v-btn>
        </v-card-actions>
      </v-card>

      </v-card>
    `,
});

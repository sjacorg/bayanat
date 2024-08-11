const ExportCard = Vue.defineComponent({
  props: ['exp', 'close', 'adminMode'],

  watch: {
    exp: function (val, old) {},
  },
  filters: {
    capitalize(value) {
      if (!value) return '';
      value = value.toString();
      return value.charAt(0).toUpperCase() + value.slice(1);
    },
  },

  mounted() {
    //convert expiry to localized date
    this.exp.expires_on = this.localDate(this.exp.expires_on, (format = false));

    this.loadExportItems();
  },

  methods: {
    loadExportItems() {
      const q = [{ ids: this.exp.items }];

      axios
        .post(`/admin/api/bulletins/?page=${this.page}&per_page=${this.per_page}`, { q: q })
        .then((res) => {
          this.items = [...this.items, ...res.data.items];
          this.showLoadMore = this.per_page * this.page < res.data.total;
          this.page += 1;
        });
    },

    showApprove(item) {
      return item.status === 'Pending' || item.status === 'Failed';
    },

    showReject(item) {
      return !(item.status === 'Rejected' || item.status === 'Expired');
    },

    showChangeExpiry(item) {
      return item.status === 'Approved';
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

      const localDate = utcDate.toLocaleString('en-US', { timeZone: userTimezone });

      if (!format) {
        //console.log((dateFns.format(localDate, 'YYYY-MM-DDTHH:m')));
        return dateFns.format(localDate, 'YYYY-MM-DDTHH:mm');
      } else {
        return localDate;
      }
    },
  },

  data: function () {
    return {
      translations: window.translations,
      expiryFieldDisabled: true,
      showLoadMore: false,
      per_page: 5,
      page: 1,
      items: [],
    };
  },

  template: `

    <v-card color="grey lighten-3" class="mx-auto pa-3">
      <v-card color="grey lighten-5"  class="header-fixed mx-2">
        <v-card-text>

          <!-- Export ID chip -->
          <v-chip pill small label color="gv darken-2" class="white--text">
            {{ translations.id_ }} #{{ exp.id }}
          </v-chip>

          <!-- Table chip -->
          <v-chip pill small label color="gv darken-2"
                  class="white--text">
            {{ exp.table.toUpperCase() }}
          </v-chip>

          <!-- File format chip -->
          <v-tooltip location="top" :text="'Export format:' + exp.file_format">
          <template #activator="{props}">
          <v-avatar size="32" v-bind="props" color="gv darken-2" label class="mx-2">

            <v-icon small center color="white" v-if="exp.file_format === 'json'">mdi-code-json</v-icon>
            <v-icon small center color="white" v-if="exp.file_format === 'pdf'">mdi-file-pdf-box</v-icon>
            <v-icon small center color="white" v-if="exp.file_format === 'csv'">mdi-file-delimited-outline</v-icon>

          </v-avatar>
          </template>
          </v-tooltip>

          <!-- Media chip -->
          <v-tooltip bottom text="'Include Media:' + exp.include_media">
          <template #activator="{props}">
          <v-avatar size="32" v-bind="props" color="grey darken-3" small label class="mx-2">

            <v-icon small center color="white" v-if="exp.include_media">mdi-paperclip-check</v-icon>
            <v-icon small center color="white" v-if="!exp.include_media">mdi-paperclip-off</v-icon>

          </v-avatar>
          </template>
          </v-tooltip>
        </v-card-text>

        <!-- Requester chip -->
        
        <v-chip prepend-icon="mdi-account-circle-outline"  class="pa-2 mx-2 my-2">
          {{ exp.requester.name }}
        </v-chip>
        
        <!-- Approver chip -->
        <v-chip prepend-icon="mdi-account-circle-outline" color="white lighten-3"  class="pa-2 mx-2 my-2" v-if="exp.approver">
          {{ exp.approver.name }}
        </v-chip>

        <!-- Status chip -->
        <v-tooltip bottom text="{{_('Status')}}">
          <template #activator="{props}">
        <v-chip color="white lighten-3" small label class="mx-2 my-2">
          <v-icon left>mdi-delta</v-icon>
          {{ exp.status }}
        </v-chip>
        </template>
        </v-tooltip>
      </v-card>

      <!-- Dates fields -->
      <div class="d-flex">
        <uni-field :caption="translations.requestedOn_" :english="localDate(exp.created_at)"></uni-field>
        <uni-field :caption="translations.expiresOn_" :english="localDate(exp.expires_on)"></uni-field>
      </div>

      <!-- Admin actions cards -->
      <v-card  class="mx-2" color="grey lighten-5" v-if="adminMode">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-2"> {{ translations.adminActions_ }}</v-toolbar-title>
        </v-toolbar>
        <v-card-text>


          <!-- Approve button -->
          <v-btn
              v-if="showApprove(exp)"
              :disabled="exp.complete"
              class="ml-2"
              @click.stop="$emit('approve', exp.id)"
              size="small"
              color="primary"
              prepend-icon="mdi-check"
          >

            {{ translations.approve_ }}
          </v-btn>

          <!-- Reject button -->
          <v-btn
              v-if="showReject(exp)"
              class="ml-2"
              @click.stop="$emit('reject', exp.id)"
              size="small"
              prepend-icon="mdi-close"
              color="error">

            <span v-if="exp.status=='Approved'">{{ translations.expireNow_ }}</span>
            <span v-else>{{ translations.reject_ }}</span>

          </v-btn>

          <!-- Change expiry date button -->
          <v-btn
              v-if="expiryFieldDisabled && showChangeExpiry(exp)"
              :disabled="exp.expired"
              class="ml-2"
              @click="changeExpiry"
              size="small"
              prepend-icon="mdi-calendar-edit"
              color="primary">
            {{ translations.changeExpiry_ }}
          </v-btn>

          <!-- Set expiry date button -->
          <v-btn
              v-if="!expiryFieldDisabled && showChangeExpiry(exp)"
              :disabled="exp.expired"
              class="ml-2"
              @click.stop="$emit('change', exp.id, exp.expires_on)"
              size="small"
              prepend-icon="mdi-calendar-edit"
              color="primary">
            {{ translations.setExpiry_ }}
          </v-btn>

        </v-card-text>

        <v-card-item>
          <!-- Expiry date text field -->
          <v-text-field
              v-if="!expiryFieldDisabled && showChangeExpiry(exp)"
              type="datetime-local"
              label="{{ translations.exportExpiry_ }}"
              v-model="exp.expires_on"
          >
          </v-text-field>
        </v-card-item>
      </v-card>

      <!-- Refs -->
      <v-card v-if="exp.ref && exp.ref.length"  class="ma-2 pa-2 d-flex align-center flex-grow-1"
              >
        <div class="text-subtitle-2 mr-2">{{ translations.ref_ }}</div>
        <v-chip x-small v-for="r in exp.ref" class="caption  mx-1">{{ r }}</v-chip>
      </v-card>

      <!-- Comment -->
      <uni-field :caption="translations.comment_" :english="exp.comment"></uni-field>

      <!-- Related Bulletins -->
      <v-card  color="grey lighten-5" class="ma-2" v-if="items">
        <v-card-text v-if="exp.table == 'bulletin'">
          <div class="pa-2 header-sticky text-subtitle-2 ">{{ translations.relatedBulletins_ }}</div>
          <bulletin-result  v-for="item in items" :bulletin="item"></bulletin-result>
        </v-card-text>

        <v-card-text v-if="exp.table == 'actor'">
          <div class="pa-2 header-sticky text-subtitle-2 ">{{ translations.relatedActors_ }}</div>
          <actor-result  v-for="item in items" :actor="item"></actor-result>
        </v-card-text>


        <v-card-text v-if="exp.table == 'incident'">
          <div class="pa-2 header-sticky text-subtitle-2 ">{{ translations.relatedIncidents_ }}</div>
          <incident-result  v-for="item in items" :incident="item"></incident-result>
        </v-card-text>


        <v-card-actions>
          <v-btn
              class="ma-auto caption"
              small
              color="grey lighten-4"
              elevation="0"
              @click="loadExportItems"
              v-if="showLoadMore"
          >{{ translations.loadMore_ }}
            <v-icon right>mdi-chevron-down</v-icon>
          </v-btn>
        </v-card-actions>
      </v-card>

    </v-card>
  `,
});

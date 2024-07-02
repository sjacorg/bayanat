const ActorProfiles = Vue.defineComponent({
  props: {
    actorId: {
      type: Number,
      required: true,
    },
    i18n: {
      type: Object,
    },
  },

  data: function () {
    return {
      actorProfiles: [],
      tab: 0,
    };
  },

  mounted() {
    this.fetchProfiles();
  },

  methods: {
    fetchProfiles() {
      axios
        .get(`/admin/api/actor/${this.actorId}/profiles`)
        .then((response) => {
          this.actorProfiles = response.data;
        })
        .catch((error) => {
          console.error('Error fetching profiles:', error);
        });
    },
  },

  template: `
      <v-card class="ma-2">
        <v-tabs v-model="tab"
                background-color="primary"
                show-arrows>
          <v-tab v-for="(profile, index) in actorProfiles" :key="index">
            {{ profile.sources?.length? profile.sources[0].title : "Profile " + (index + 1) }}
          </v-tab>
        </v-tabs>

        <v-window v-model="tab">
          <v-window-item class="pa-2" v-for="(profile, index) in actorProfiles" :key="index">
            <v-card flat>
              <v-tooltip v-if="profile.originid" location="bottom">
                <template v-slot:activator="{ props }">
                    <v-chip
                      v-bind="props"
                      prepend-icon="mdi-identifier" 
                      :href="profile.source_link" 
                      target="_blank" 
                      label
                      append-icon="mdi-open-in-new"
                      class="ml-2">
                      {{ profile.originid }}
                    </v-chip>
                </template>
                {{ i18n.originid_ }}
              </v-tooltip>

              <v-card outlined class="ma-2" color="grey" v-if="profile.sources?.length">
                <v-card-text>
                  <div class="px-1 title black--text">{{ i18n.sources_ }}</div>
                  <v-chip-group column>
                    <v-chip small label color="blue-grey" v-for="source in profile.sources" :key="source.id">
                      {{ source.title }}
                    </v-chip>
                  </v-chip-group>
                </v-card-text>
              </v-card>

              <v-card outlined class="ma-2" color="grey" v-if="profile.labels?.length">
                <v-card-text>
                  <div class="px-1 title black--text">{{ i18n.labels_ }}</div>
                  <v-chip-group column>
                    <v-chip small label color="blue-grey" v-for="label in profile.labels" :key="label.id">
                      {{ label.title }}
                    </v-chip>
                  </v-chip-group>
                </v-card-text>
              </v-card>


              <v-card outlined class="ma-2" color="grey" v-if="profile.ver_labels?.length">
                <v-card-text>
                  <div class="px-1 title black--text">{{ i18n.verifiedLabels_ }}</div>
                  <v-chip-group column>
                    <v-chip small label color="blue-grey" v-for="verLabel in profile.ver_labels"
                            :key="verLabel.id">
                      {{ verLabel.title }}
                    </v-chip>
                  </v-chip-group>
                </v-card-text>
              </v-card>

              <v-card v-if="profile.description" class="ma-2 mb-4">
                <v-toolbar density="compact">
                  <v-toolbar-title class="text-subtitle-1">{{ i18n.description_ }}</v-toolbar-title>
                </v-toolbar>

                <v-card-text class="text-body-2 " v-html="profile.description"></v-card-text>
              </v-card>

              <mp-card v-if="profile.mode === 3" :i18n="i18n" :profile-id="profile.id"></mp-card>

              <uni-field :caption="i18n.publishDate_" :english="profile.publish_date"></uni-field>
              <uni-field :caption="i18n.documentationDate_" :english="profile.documentation_date"></uni-field>

            </v-card>
          </v-window-item>
        </v-window>
      </v-card>
    `,
});

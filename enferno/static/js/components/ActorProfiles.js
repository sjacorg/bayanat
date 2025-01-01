const ActorProfiles = Vue.defineComponent({
  props: {
    actorId: {
      type: Number,
      required: true,
    },
  },

  data: function () {
    return {
      translations: window.translations,
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
      <v-card variant="plain" class="rounded-0">
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
                {{ translations.originid_ }}
              </v-tooltip>

              <v-card class="ma-2" v-if="profile.sources?.length">
                <v-card-text>
                  <div class="px-1 title black--text">{{ translations.sources_ }}</div>
                  <div class="flex-chips">
                    <v-chip size="small" class="flex-chip" label v-for="source in profile.sources" :key="source.id">
                      {{ source.title }}
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>

              <v-card class="ma-2" v-if="profile.labels?.length">
                <v-card-text>
                  <div class="px-1 title black--text">{{ translations.labels_ }}</div>
                  <div class="flex-chips">
                    <v-chip size="small" class="flex-chip" label v-for="label in profile.labels" :key="label.id">
                      {{ label.title }}
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>


              <v-card class="ma-2" v-if="profile.ver_labels?.length">
                <v-card-text>
                  <div class="px-1 title black--text">{{ translations.verifiedLabels_ }}</div>
                  <div class="flex-chips">
                    <v-chip size="small" class="flex-chip" label v-for="verLabel in profile.ver_labels"
                            :key="verLabel.id">
                      {{ verLabel.title }}
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>

              <v-card v-if="profile.description" class="ma-2 mb-4">
                <v-toolbar density="compact">
                  <v-toolbar-title class="text-subtitle-1">{{ translations.description_ }}</v-toolbar-title>
                </v-toolbar>

                <v-card-text class="text-body-2 " v-html="profile.description"></v-card-text>
              </v-card>

              <mp-card v-if="profile.mode === 3" :profile-id="profile.id"></mp-card>

              <uni-field :caption="translations.publishDate_" :english="profile.publish_date"></uni-field>
              <uni-field :caption="translations.documentationDate_" :english="profile.documentation_date"></uni-field>

            </v-card>
          </v-window-item>
        </v-window>
      </v-card>
    `,
});

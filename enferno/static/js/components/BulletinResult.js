const BulletinResult = Vue.defineComponent({
  props: ['bulletin', 'hidden', 'showHide'],

  data: () => {
    return {
      translations: window.translations,
      hide: this.hidden || false,
    }
  },

  template: `
    <template v-if="!hide">
      <v-card v-if="!bulletin.restricted" hover class="ma-2">
        <v-toolbar density="compact" class="d-flex px-2">
          <v-chip color="primary" variant="flat" size="small">{{ translations.id_ }} {{ bulletin.id }}</v-chip>
          <v-chip variant="text" :href="bulletin.source_link" target="_blank" class="white--text ml-1" label
                  size="small"># {{ bulletin.originid }}
          </v-chip>
          <v-spacer></v-spacer>
          <v-chip variant="text" v-if="bulletin.publish_date" size="small">{{ bulletin.publish_date }}</v-chip>
        </v-toolbar>
        <v-card-title class="text-subtitle-2">{{bulletin.title}}</v-card-title>
        <v-divider></v-divider>
        <slot name="header"></slot>
        
        
        <v-card-text>
        
            



              <v-list-item v-if="bulletin.locations?.length" :title="translations.locations_">
                <v-list-item-subtitle>
                  <v-chip-group column>
                    <v-chip size="small" v-for="location in bulletin.locations" :key="location">
                      {{ location.full_string }}
                    </v-chip>
                  </v-chip-group>
                </v-list-item-subtitle>
              </v-list-item>


              <v-list-item v-if="bulletin.sources?.length" :title="translations.sources_">
                <v-list-item-subtitle>
                  <v-chip-group
                      column
                  >
                    <v-chip size="small" color="grey" v-for="source in bulletin.sources" :key="source">
                      {{ source.title }}
                    </v-chip>
                  </v-chip-group>
                </v-list-item-subtitle>

              </v-list-item>
          
        
        </v-card-text>
        
        <v-card-actions class="justify-end">
          <slot name="actions"></slot>
          <v-btn size="small" v-if="showHide" @click="hide=true" variant="plain"> {{ translations.hide_ }}</v-btn>
          <v-btn size="small" icon="mdi-eye"
                 @click.capture="$root.previewItem('/admin/api/bulletin/'+bulletin.id+'?mode=3')"
                 color="primary">

          </v-btn>
        </v-card-actions>
      </v-card>

      <v-card disabled elevation="0" v-else class="restricted">

        <v-card-text>{{ bulletin.id }} - {{ translations.restricted_ }}</v-card-text>

      </v-card>
    </template>
  `,
});

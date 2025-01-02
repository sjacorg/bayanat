const ActorResult = Vue.defineComponent({
  props: ['actor', 'hidden', 'showHide'],
  
  data: () => {
    return {
      translations: window.translations,
      hide: this.hidden || false,
    }
  },

  template: `
    <template v-if="!hide">
      <v-card hover class="ma-2" v-if="!actor.restricted">
        <v-toolbar density="compact" class="d-flex px-2">
          <v-chip color="primary" variant="flat" size="small">{{ translations.id_ }} {{ actor.id }}</v-chip>
          <v-chip v-if="actor.originid" variant="text" class="ml-1"># {{ actor.originid }}</v-chip>
          <v-spacer></v-spacer>
          <v-chip variant="text" v-if="actor.publish_date" size="small">{{ actor.publish_date }}</v-chip>
        </v-toolbar>
        <v-card-title class="text-subtitle-2 text-wrap text-break">{{actor.name}}</v-card-title>
        <v-divider></v-divider>
        <slot name="header"></slot>
        <v-card-text>
                <v-list-item v-if="actor.sources?.length" :title="translations.sources_">
                  <v-list-item-subtitle>
                    <div class="flex-chips">
                      <v-chip class="flex-chip" size="small" v-for="source in actor.sources" :key="source">
                        {{ source.title }}
                      </v-chip>
                    </div>
                  </v-list-item-subtitle>

                </v-list-item>



        </v-card-text>


        <v-card-actions class="justify-end">
          <slot name="actions"></slot>
          <v-btn v-if="showHide" @click="hide=true" size="small" variant="plain" > {{ translations.hide_ }}</v-btn>
          <v-btn icon="mdi-eye"  size="small" color="primary"
                 @click.capture="$root.previewItem('/admin/api/actor/'+actor.id+'?mode=3')">
          </v-btn>
        </v-card-actions>
      </v-card>

      <v-card disabled elevation="0" v-else class="restricted">
        <v-card-text>{{ actor.id }} - {{ translations.restricted_ }}</v-card-text>
      </v-card>


    </template>
  `,
});

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
          <v-chip variant="text" v-if="actor.publish_date" size="small">{{ $root.formatDate(actor.publish_date) }}</v-chip>
        </v-toolbar>
        <v-card-title class="text-wrap text-break">
          <v-row>
            <template v-if="actor.name || actor.name_ar">
              <v-col><uni-field disable-spacing :caption="translations.name_" :english="actor.name" :arabic="actor.name_ar"></uni-field></v-col>
            </template>
            <template v-else>
              <v-col><uni-field disable-spacing :caption="translations.firstName_" :english="actor.first_name" :arabic="actor.first_name_ar"></uni-field></v-col>
              <v-col><uni-field disable-spacing :caption="translations.lastName_" :english="actor.last_name" :arabic="actor.last_name_ar"></uni-field></v-col>
            </template>
          </v-row>
        </v-card-title>
        <v-divider></v-divider>
        <slot name="header"></slot>

        <v-card-text v-if="actor.sources?.length">
          <v-list-item :title="translations.sources_">
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
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-btn
                v-bind="props"
                @click.capture="$root.previewItem('/admin/api/actor/'+actor.id+'?mode=3')"
                color="secondary"
                variant="outlined"
                icon="mdi-magnify-expand"
                size="small"
              ></v-btn>
            </template>
            {{ translations.preview_ }}
          </v-tooltip>
          <v-tooltip v-if="showHide" location="bottom">
            <template v-slot:activator="{ props }">
              <v-btn
                v-bind="props"
                @click="hide=true"
                color="secondary"
                variant="outlined"
                icon="mdi-minus"
                size="small"
              ></v-btn>
            </template>
            {{ translations.hideFromResults_ }}
          </v-tooltip>
        </v-card-actions>
      </v-card>

      <v-card disabled elevation="0" v-else class="restricted">
        <v-card-text>{{ actor.id }} - {{ translations.restricted_ }}</v-card-text>
      </v-card>


    </template>
  `,
});

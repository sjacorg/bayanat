const EventCard = Vue.defineComponent({
  props : ['event', 'number'],
  data: () => ({
    translations: window.translations,
  }),
  template: `

    <v-card hover min-width="300px" height="100%" class="event-card pa-3 mb-2 mt-1">
      <v-card-text class="align-center ga-2">
        <v-chip
          color="teal"
          size="small"
          class="mr-2"
        >
          #{{ number }}
        </v-chip>

        <v-chip
            v-if="event.eventtype"
            color="teal"
            size="small"
            class="mr-2"
        >{{ event.eventtype?.title }}
        </v-chip>

        <div class="text-subtitle-2 d-flex mt-2 text-wrap text-break">
          {{ event.title }}
           <v-tooltip v-if="event.estimated" location="bottom">
              <template v-slot:activator="{ props }">
                <v-icon v-bind="props" icon="mdi-information" class="ml-2"></v-icon>
              </template>
              {{ translations.timingForThisEventIsEstimated_ }}
            </v-tooltip>
        </div>
        
        
        

      </v-card-text>
      <v-card-text class="text-caption pt-0">

        <div v-if="event.comments">
          {{ event.comments }}
        </div>


        <v-spacer></v-spacer>

        <v-chip prepend-icon="mdi-map-marker" class="my-2 flex-chip" v-if="event.location?.full_string" label>
          {{ event.location.full_string }}
        </v-chip>


        <div v-if="event.from_date||event.to_date">
          <v-divider class="my-2"></v-divider>
          
          <v-chip prepend-icon="mdi-calendar" label variant="text"  class="text-caption" v-if="event.from_date">
            {{ event.from_date }}
          </v-chip>
          <span class="caption" v-if="event.to_date">
            <v-icon icon="mdi-arrow-right" class="mr-1"></v-icon>
            {{ event.to_date }}
          </span>
        </div>
      </v-card-text>

      <slot name="actions"></slot>


    </v-card>


  `,
});

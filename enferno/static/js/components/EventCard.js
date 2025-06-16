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
          <uni-field :caption="translations.title_" :english="event.title" :arabic="event.title_ar" disable-spacing></uni-field>
        </div>

        <div v-if="event.comments">
          <uni-field :caption="translations.comments_" :english="event.comments" :arabic="event.comments_ar" disable-spacing></uni-field>
        </div>


        <v-spacer></v-spacer>

        <v-chip prepend-icon="mdi-map-marker" class="my-2 flex-chip" v-if="event.location?.full_string" label>
          {{ event.location.full_string }}
        </v-chip>

        <v-divider v-if="event.from_date || event.to_date || event.estimated" class="my-2"></v-divider>

        <div v-if="event.from_date || event.to_date">
          <v-chip prepend-icon="mdi-calendar" label variant="text"  class="text-caption" v-if="event.from_date">
            {{ event.from_date }}
          </v-chip>
          <span class="caption" v-if="event.to_date">
            <v-icon icon="mdi-arrow-right" class="mr-1"></v-icon>
            {{ event.to_date }}
          </span>
        </div>
        
        <div v-if="event.estimated" class="text-caption text-medium-emphasis d-flex align-center ml-1"><v-icon icon="mdi-information" class="mr-1"></v-icon> {{ translations.timingForThisEventIsEstimated_ }}</div>
      </v-card-text>

      <slot name="actions"></slot>


    </v-card>


  `,
});

const EventCard = Vue.defineComponent({
    props : ['event', 'number', 'i18n'],

  template: `

    <v-card min-width="300px" height="100%" class="event-card pa-3 mb-2 mt-1">
      <v-card-text class="align-center ga-2">
        
        <v-icon v-if="event.estimated"  color="orange lighten-4">mdi-information</v-icon>
        <v-chip
            
            v-if="event.eventtype"
            color="teal"
            size="small"
            class="mr-2"
        >{{ event.eventtype.title }}
        </v-chip>


        <span class="text-subtitle-2 ">{{ event.title }}</span>
        
        
        <v-avatar  class="text-caption float-end" size="small" variant="tonal">{{ number }}
        </v-avatar>

      </v-card-text>
      <v-card-text class="text-caption">

        <div v-if="event.comments">
          {{ event.comments }}
        </div>


        <v-spacer></v-spacer>

        <v-chip class="my-2" color="grey lighten-4" size="small" v-if="event.location && event.location.full_string"
                label>
          <v-icon size="x-small" left>mdi-map-marker</v-icon>
          <span class="caption font-italic">{{ event.location.full_string }}</span>
        </v-chip>


        <div v-if="event.from_date||event.to_date">
          <v-divider class="my-2"></v-divider>
          <v-icon size="small" left>mdi-calendar</v-icon>
          <span class="mr-1 caption" v-if="event.from_date">
        {{ event.from_date }}
      </span>
          <span class="caption" v-if="event.to_date">
        -> {{ event.to_date }}
      </span>
        </div>
      </v-card-text>

      <slot name="actions"></slot>


    </v-card>


  `,
});

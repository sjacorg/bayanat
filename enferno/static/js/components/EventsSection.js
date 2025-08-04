const getDefaultEvent = () => ({
  title: '',
  from_date: '',
  to_date: '',
});

const EventsSection = Vue.defineComponent({
  props: {
    editedItem: { type: Object },
    dialogProps: { type: Object },
    eventParams: { type: Object },
    showCopyIcon: { type: Boolean },
    advFeatures: { type: Boolean },
  },
  emits: ['update:modelValue'],
  data: () => ({
    validationRules: validationRules,
    translations: window.translations,
    valid: false,
    eventDialog: false,
    editedEventIndex: -1,
    editedEvent: getDefaultEvent(),
  }),
  computed: {
    allowedDateFrom() {
      if (this.editedEvent?.to_date) {
        // ensure date is not after the to_date
        return (current) => current <= dayjs(this.editedEvent.to_date).toDate();
      }
      return () => true;
    },
    allowedDateTo() {
      if (this.editedEvent?.from_date) {
        // ensure date is not before the from_date
        return (current) => current >= dayjs(this.editedEvent.from_date).toDate();
      }
      return () => true;
    },
  },
  methods: {
    validateEventForm() {
      const e = this.editedEvent;

      const hasDateOrLocation = !!(e.location || e.from_date || e.to_date);
      const hasTitleOrType = !!(e.title || e.title_ar || e.eventtype);

      const missing = [];
      if (!hasDateOrLocation) missing.push(this.translations.locationOrDateRequired_);
      if (!hasTitleOrType) missing.push(this.translations.titleOrTypeRequired_);

      if (missing.length > 0) {
        this.$root.showSnack(missing.join('<br />'));
        return false;
      }

      return true;
    },
    validateForm() {
      this.$refs.form.validate().then(({ valid, errors }) => {
        if (!this.validateEventForm()) return

        if (valid) {
          this.saveEvent();
        } else {
          this.$root.showSnack(translations.pleaseReviewFormForErrors_);
          scrollToFirstError(errors);
        }
      });
    },
    saveEvent() {
      if (this.editedEventIndex > -1) {
        Object.assign(this.editedItem.events[this.editedEventIndex], this.editedEvent);
        //update record
      } else {
        this.editedItem.events.push(this.editedEvent);
        //create new record
      }
      this.closeEvent();
    },
    removeEvent(evt, index) {
      if (confirm(translations.confirmDeleteEvent_)) {
        this.editedItem.events.splice(index, 1);
      }
    },
    editEvent(evt, item, index) {
      this.eventDialog = true;

      this.$nextTick(() => {
        this.editedEvent = Object.assign({}, item);

        this.editedEventIndex = index;
      });
    },
    closeEvent() {
      this.eventDialog = false;
      setTimeout(() => {
        this.editedEvent = getDefaultEvent();
        this.editedEventIndex = -1;
      }, 300);
    },
  },
  template: /*html*/ `
    <v-card>
        <v-toolbar>
            <v-toolbar-title>{{ translations.events_ }}</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-btn
                    color="primary"
                    @click="eventDialog = true"
                    icon="mdi-plus-circle"
            ></v-btn>

        </v-toolbar>


        <v-card-text>
            <v-container fluid>
                <v-row>


                    <v-col
                            class="pa-2 d-flex v-col-auto"

                            v-for="(event,index) in editedItem.events"
                            :key="index"
                    >
                        <event-card :number="index+1" :event="event">

                            <template v-slot:actions>
                                <v-card-actions class="justify-end">

                                    <v-btn
                                            @click="editEvent($event,event,index)"
                                            size="small"
                                            icon="mdi-pencil"
                                    ></v-btn>
                                    <v-btn
                                            @click="removeEvent($event,index)"
                                            size="small"
                                            color="red"
                                            icon="mdi-delete-sweep"

                                    ></v-btn
                                    >
                                </v-card-actions>
                            </template>
                        </event-card>
                    </v-col>
                </v-row>
            </v-container>
        </v-card-text>
    </v-card>


    <v-dialog v-model="eventDialog" v-bind="dialogProps || { 'max-width': '880px' }">
        <v-card>
            <v-toolbar color="dark-primary">
                <v-toolbar-title>{{ translations.event_ }}</v-toolbar-title>
                <v-spacer></v-spacer>
            
                <template #append>
                    <v-btn variant="elevated" @click="validateForm" class="mx-2">{{ translations.save_ }}</v-btn>
                    <v-btn icon="mdi-close" @click="closeEvent"></v-btn>
                </template>
            </v-toolbar>

            <v-form @submit.prevent="validateForm" ref="form" v-model="valid">
                <v-card-text>
                    <v-container>
                        <v-row>
                            <v-col cols="12" md="6">
                                <dual-field v-model:original="editedEvent.title"
                                            v-model:translation="editedEvent.title_ar"
                                            :label-original="translations.title_"
                                            :label-translation="translations.titleAr_"
                                            :rules="[
                                              validationRules.maxLength(255),
                                            ]">
                                </dual-field>
                            </v-col>

                            <v-col cols="12" md="6">
                                <dual-field v-model:original="editedEvent.comments"
                                            v-model:translation="editedEvent.comments_ar"
                                            :label-original="translations.comments_"
                                            :label-translation="translations.commentsAr_"
                                ></dual-field>
                            </v-col>
                        </v-row>

                        <v-row>
                            <v-col cols="12" md="8">
                                <location-search-field
                                        v-model="editedEvent.location"
                                        api="/admin/api/locations/"
                                        item-title="full_string"
                                        item-value="id"
                                        :multiple="false"
                                        :show-copy-icon="advFeatures"
                                        :label="translations.location_"
                                ></location-search-field>


                            </v-col>
                            <v-col md="4">

                                <search-field
                                        v-model="editedEvent.eventtype"
                                        api="/admin/api/eventtypes/"
                                        :query-params="eventParams"
                                        item-title="title"
                                        item-value="id"
                                        :multiple="false"
                                        :label="translations.eventType_"
                                ></search-field>


                            </v-col>
                        </v-row>

                        <v-row>
                            <v-col cols="12" md="6" class="text-center">
                                <pop-date-time-field :allowed-dates="allowedDateFrom" :time-label="translations.time_" :label="translations.from_" v-model="editedEvent.from_date"></pop-date-time-field>
                            </v-col>
                            <v-col cols="12" md="6">
                                <pop-date-time-field :allowed-dates="allowedDateTo" :time-label="translations.time_" :label="translations.to_" v-model="editedEvent.to_date"></pop-date-time-field>
                            </v-col>
                        </v-row>
                        <v-row>
                            <v-col md="4">
                                <v-switch
                                        color="primary"
                                        :label="translations.estimatedTime_"
                                        v-model="editedEvent.estimated"
                                ></v-switch>
                            </v-col>
                        </v-row>
                    </v-container>

                    <v-alert density="compact" variant="tonal" type="info" class="my-4">
                        {{ translations.pleaseFillAtLeaseOneFieldEventSection_ }}
                    </v-alert>
                </v-card-text>
            </v-form>
        </v-card>
    </v-dialog>
    `,
});

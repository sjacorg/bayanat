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
    hasDateOrLocation() {
      const e = this.editedEvent;
      return !!(e.location || e.from_date || e.to_date);
    },
    hasTitleOrType() {
      const e = this.editedEvent;
      return !!(e.title || e.title_ar || e.eventtype);
    },
    // Show asterisk only if the group is not yet satisfied
    showTitleTypeAsterisk() {
      return !this.hasTitleOrType;
    },
    showLocationDateAsterisk() {
      return !this.hasDateOrLocation;
    },
    // Validation rules for groups
    titleOrTypeRule() {
      return () => this.hasTitleOrType || this.translations.titleOrTypeRequired_;
    },
    locationOrDateRule() {
      return () => this.hasDateOrLocation || this.translations.locationOrDateRequired_;
    },
  },
  watch: {
    // Watch for changes in title/type group
    'editedEvent.title'() {
      this.validateTitleTypeGroup();
    },
    'editedEvent.title_ar'() {
      this.validateTitleTypeGroup();
    },
    'editedEvent.eventtype'() {
      this.validateTitleTypeGroup();
    },
    // Watch for changes in location/date group
    'editedEvent.location'() {
      this.validateLocationDateGroup();
    },
    'editedEvent.from_date'() {
      this.validateLocationDateGroup();
    },
    'editedEvent.to_date'() {
      this.validateLocationDateGroup();
    },
  },
  methods: {
    validateTitleTypeGroup() {
      // Trigger validation on the next tick to ensure the form is updated
      this.$nextTick(() => {
        if (this.$refs.form) {
          this.$refs.form.validate();
        }
      });
    },
    validateLocationDateGroup() {
      this.$nextTick(() => {
        if (this.$refs.form) {
          this.$refs.form.validate();
        }
      });
    },
    validateFormAndSave() {
      this.$refs.form.validate().then(({ valid, errors }) => {
        if (valid) {
          this.saveEvent();
        } else {
          this.$root.showSnack(translations.pleaseReviewFormForErrors_);
          scrollToFirstError();
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


    <div :class="['position-fixed h-screen right-0 top-0 z-100', { 'pointer-events-none': !eventDialog }]" :style="$root?.rightDialogProps?.['content-props']?.style">
    <div class="position-relative h-100 w-100">
    <v-dialog v-model="eventDialog" v-bind="dialogProps || { 'max-width': '880px' }">
        <v-card elevation="4">
            <v-toolbar color="dark-primary">
                <v-toolbar-title>{{ translations.event_ }}</v-toolbar-title>
                <v-spacer></v-spacer>

                <template #append>
                    <v-btn 
                        variant="elevated" 
                        @click="validateFormAndSave" 
                        class="mx-2"
                    >
                        {{ translations.save_ }}
                    </v-btn>
                    <v-btn icon="mdi-close" @click="closeEvent"></v-btn>
                </template>
            </v-toolbar>

            <v-form @submit.prevent="validateFormAndSave" ref="form" v-model="valid">
                <v-card-text>
                    <v-container>
                        <!-- Info banner explaining requirements -->
                        <v-alert 
                            type="info" 
                            variant="tonal" 
                            density="compact" 
                            class="mb-6"
                        >
                            <div class="text-body-2">
                                <strong>{{ translations.requiredFields_ }}:</strong>
                                <div class="mt-1">
                                    • {{ translations.titleOrTypeRequired_ }}
                                </div>
                                <div>
                                    • {{ translations.locationOrDateRequired_ }}
                                </div>
                            </div>
                        </v-alert>

                        <v-row>
                            <v-col cols="12" md="6">
                                <dual-field 
                                    v-model:original="editedEvent.title"
                                    v-model:translation="editedEvent.title_ar"
                                    :rules="[
                                        validationRules.maxLength(255),
                                        titleOrTypeRule
                                    ]"
                                >
                                    <template #label-original>
                                        {{ translations.title_ }} <Asterisk v-if="showTitleTypeAsterisk" />
                                    </template>
                                    <template #label-translation>
                                        {{ translations.titleAr_ }} <Asterisk v-if="showTitleTypeAsterisk" />
                                    </template>
                                </dual-field>
                            </v-col>

                            <v-col cols="12" md="6">
                                <dual-field 
                                    v-model:original="editedEvent.comments"
                                    v-model:translation="editedEvent.comments_ar"
                                    :label-original="translations.comments_"
                                    :label-translation="translations.commentsAr_"
                                    :rules="[validationRules.maxLength(255)]"
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
                                    :rules="[locationOrDateRule]"
                                >
                                    <template v-slot:label>
                                        {{ translations.location_ }} <Asterisk v-if="showLocationDateAsterisk" />
                                    </template>
                                </location-search-field>
                            </v-col>
                            
                            <v-col cols="12" md="4">
                                <search-field
                                    v-model="editedEvent.eventtype"
                                    api="/admin/api/eventtypes/"
                                    :query-params="eventParams"
                                    item-title="title"
                                    item-value="id"
                                    :multiple="false"
                                    :rules="[titleOrTypeRule]"
                                >
                                    <template v-slot:label>
                                        {{ translations.eventType_ }} <Asterisk v-if="showTitleTypeAsterisk" />
                                    </template>
                                </search-field>
                            </v-col>
                        </v-row>

                        <v-row>
                            <v-col cols="12" md="6">
                                <pop-date-time-field 
                                    v-model="editedEvent.from_date"
                                    :rules="[
                                        validationRules.date(), 
                                        validationRules.dateBeforeOtherDate(editedEvent.to_date),
                                        locationOrDateRule
                                    ]" 
                                    :allowed-dates="allowedDateFrom" 
                                    :time-label="translations.time_"
                                >
                                    <template #label>
                                        {{ translations.from_ }} <Asterisk v-if="showLocationDateAsterisk" />
                                    </template>
                                </pop-date-time-field>
                            </v-col>
                            
                            <v-col cols="12" md="6">
                                <pop-date-time-field 
                                    v-model="editedEvent.to_date"
                                    :rules="[
                                        validationRules.date(), 
                                        validationRules.dateAfterOtherDate(editedEvent.from_date),
                                        locationOrDateRule
                                    ]" 
                                    :allowed-dates="allowedDateTo" 
                                    :time-label="translations.time_"
                                >
                                    <template #label>
                                        {{ translations.to_ }} <Asterisk v-if="showLocationDateAsterisk" />
                                    </template>
                                </pop-date-time-field>
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
                </v-card-text>
            </v-form>
        </v-card>
    </v-dialog>
    </div>
    </div>
    `,
});
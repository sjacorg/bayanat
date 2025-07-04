const defaultActorData = {
  description: '',
  type: 'Person',
  // related events
  events: [],
  // related media
  medias: [],
  // related actors
  actor_relations: [],
  // related bulletins
  bulletin_relations: [],
  // related incidents
  incident_relations: [],
  publish_date: '',
  documentation_date: '',
  actor_profiles: [
    {
      mode: 1,
    },
  ],
  roles: [],
};

const allowedKeys = [
  'first_name',
  'first_name_ar',
  'middle_name',
  'middle_name_ar',
  'last_name',
  'last_name_ar',
  'sex',
  'civilian',
  'origin_place',
  'id_number',
  'tags',
  'comments',
  'status',
  'roles'
  // add others if needed
];

const ShortActorDialog = Vue.defineComponent({
  props: {
    parentItem: {
      type: Object,
      default: () => null,
    },
    canRestrictView: {
      type: Boolean,
      default: false,
    },
    statusItems: {
      type: Array,
      default: () => [],
    },
    dialogProps: {
      type: Object,
      default: () => ({}),
    },
    allowedRoles: {
      type: Array,
      default: () => [],
    },
    advFeatures: {
      type: Boolean,
      default: false,
    },
    rules: {
      type: Object,
      default: () => {},
    },
    open: {
      type: Boolean,
      default: false,
    },
    showSnack: {
      type: Function,
    },
  },
  emits: ['update:open', 'close', 'createActor'],
  data: () => ({
    editedItem: { ...defaultActorData },
    relation: {
      probability: null,
      related_as: null,
      comment: null,
    },
    valid: false,
    unrestricted: false,
    translations: window.translations,
    validationRules: validationRules,
    tab: 0,
    profileModes: [
      { id: 1, title: "{{ _('Normal')}}", fields: ['source'] }, // Normal Profile
      { id: 2, title: "{{ _('Main')}}", fields: [] }, // Main Profile
      { id: 3, title: "{{ _('Missing Person')}}", fields: ['source', 'mp'] }, // Missing Person Profile
    ],
    saving: false,
  }),
  computed: {
    formTitle() {
      return this.editedItem?.id ? this.translations.editActor_ : this.translations.newActor_;
    },
  },
  methods: {
    shouldDisplayField(mode, fieldName) {
      return this.profileModes.find((x) => x.id === mode).fields.includes(fieldName);
    },
    confirmClose() {
      if (confirm(translations.confirm_)) {
        this.close();
      }
    },
    close() {
      this.$emit('update:open', false);
      setTimeout(() => {
        this.editedItem = { ...defaultActorData };
        this.unrestricted = false;
        this.saving = false;
      }, 300);
    },
    validateForm() {
      this.$refs.form.validate().then(({ valid, errors }) => {
        if (valid) {
          this.save();
        } else {
          this.showSnack(translations.pleaseReviewFormForErrors_);
          scrollToFirstError(errors);
        }
      });
    },
    save() {
      if (!this.valid) {
        this.showSnack(translations.pleaseReviewFormForErrors_);
        return;
      }

      this.saving = true;

      // If parent id is present create relation immediately
      if (this.parentItem.id) {
        this.editedItem.bulletin_relations = [
          {
            bulletin: this.parentItem,
            probability: this.relation.probability,
            related_as: this.relation.related_as,
            comment: this.relation.comment,
          },
        ];
      }

      //create new record
      axios
        .post('/admin/api/actor/', {
          item: this.editedItem,
        })
        .then((response) => {
          if (response?.data?.item?.id) {
            this.$emit('createActor', {
              item: { ...response.data.item },
              relation: {
                probability: this.relation.probability,
                related_as: this.relation.related_as,
                comment: this.relation.comment,
              },
            });
            // Reset filters values on RelateActors component
            this.$root.$refs.relateActors.q = {}
          }
          this.showSnack(response.data.message);
          this.close();
        })
        .catch((err) => {
          console.error(err.response?.data);
          this.showSnack(handleRequestError(err));
          this.saving = false;
        });
    },
  },
  watch: {
    parentItem: {
      handler(newParentItem) {
        this.editedItem.comments = `First Data Analysis from Bulletin ${newParentItem.id ? '#' + newParentItem.id : ''}`;
        this.editedItem.status = 'Machine Created';
        this.editedItem.roles = newParentItem.roles;
        const actorProfile = this.editedItem.actor_profiles.find(Boolean);
        actorProfile.sources = newParentItem.sources;

        // Extract prefilled data from relateActors component,
        // but only the keys used in this short actor dialog form
        const relateData = this.$root.$refs.relateActors.q;
        const filteredData = Object.fromEntries(
          Object.entries(relateData).filter(([key]) => allowedKeys.includes(key))
        );

        this.editedItem = {
          ...this.editedItem,
          ...filteredData,
        };
      },
      deep: true,
      immediate: true,
    },
  },
  template: /*html*/ `
    <v-dialog
        :modelValue="open"
        v-bind="dialogProps"
    >
      <v-toolbar color="dark-primary">
        <v-toolbar-title>{{ formTitle }}</v-toolbar-title>
        <v-spacer></v-spacer>

        <template #append>
          <v-btn @click="validateForm" :disabled="saving" :loading="saving" variant="elevated" class="mx-2" style="width: 130px;">
              {{ translations.saveActor_ }}
          </v-btn>
          <v-btn icon="mdi-close" @click="confirmClose"></v-btn>
        </template>
      </v-toolbar>
      <v-form @submit.prevent="save" ref="form" v-model="valid">
          <v-card class="overflow-hidden">
              <v-sheet id="card-content" class="overflow-y-auto">
                  <v-card-text>
                      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; align-items: start;">
                          <div style="min-width: 0;">
                              <dual-field
                                  v-model:original="editedItem.first_name"
                                  v-model:translation="editedItem.first_name_ar"
                                  :label-original="translations.firstName_"
                                  :label-translation="translations.firstNameAr_"
                                  :allow-unknown="true"
                                  :rules="[
                                    validationRules.required(),
                                    validationRules.maxLength(255),
                                  ]"
                              />
                          </div>
                          <div style="min-width: 0;">
                              <dual-field
                                v-model:original="editedItem.middle_name"
                                v-model:translation="editedItem.middle_name_ar"
                                :label-original="translations.middleName_"
                                :label-translation="translations.middleNameAr_"
                                :rules="[validationRules.maxLength(255)]">
                              </dual-field>
                          </div>
                          <div style="min-width: 0;">
                              <dual-field
                                  v-model:original="editedItem.last_name"
                                  v-model:translation="editedItem.last_name_ar"
                                  :label-original="translations.lastName_"
                                  :label-translation="translations.lastNameAr_"
                                  :allow-unknown="true"
                                  :rules="[
                                      validationRules.required(),
                                      validationRules.maxLength(255),
                                  ]"
                              ></dual-field>
                          </div>

                          <div style="min-width: 0;">
                              <v-select :items="translations.actorSex" item-title="tr" item-value="en" v-model="editedItem.sex" clearable :label="translations.sex_"></v-select>
                          </div>

                          <div style="min-width: 0;">
                              <v-select :items="translations.actorCivilian" v-model="editedItem.civilian" item-title="tr" item-value="en" clearable :label="translations.civilianNonCivilian_"></v-select>
                          </div>

                          <div style="min-width: 0;">
                              <location-search-field
                                  v-model="editedItem.origin_place"
                                  api="/admin/api/locations/"
                                  item-title="full_string"
                                  item-value="id"
                                  :multiple="false"
                                  :show-copy-icon="advFeatures"
                                  :label="translations.placeOfOrigin_"
                              ></location-search-field>
                          </div>

                          <div style="min-width: 0;">
                              <v-text-field v-model="editedItem.id_number" :label="translations.idNumber_"></v-text-field>
                          </div>

                          <div style="min-width: 0;">
                              <v-combobox chips multiple v-model="editedItem.tags" :label="translations.tags_"></v-combobox>
                          </div>

                          <div v-if="editedItem.actor_profiles?.length" class="position-relative" style="grid-column: 1 / -1; min-width: 0;">
                              <v-window class="w-100 border" v-model="tab">
                                  <v-window-item v-for="(profile, index) in editedItem.actor_profiles" :key="index">
                                      <v-card class="pa-3" variant="text">
                                          <!-- Source Link -->
                                          <v-card-text v-if="shouldDisplayField(profile.mode, 'source')">
                                              <v-text-field class="mx-2" variant="outlined" v-model="profile.originid" :disabled="profile.originidDisabled" :label="translations.originId_"></v-text-field>
                                          </v-card-text>

                                          <v-card-text>
                                              <!-- Sources -->
                                              <search-field v-model="profile.sources" api="/admin/api/sources/" item-title="title" item-value="id" :multiple="true" :label="translations.sources_"></search-field>
                                          </v-card-text>

                                          <v-card-text>
                                              <!-- Labels -->
                                              <search-field v-model="profile.labels" api="/admin/api/labels/" item-title="title" item-value="id" :multiple="true" :show-copy-icon="advFeatures" :label="translations.labels_"></search-field>
                                          </v-card-text>
                                      </v-card>
                                  </v-window-item>
                              </v-window>
                          </div>

                          <div style="grid-column: 1 / -1; min-width: 0;">
                              <slot name="events"></slot>
                          </div>

                          <div style="grid-column: 1 / -1; min-width: 0;">
                            <relation-card
                              v-model:relation="relation"
                              :multi-relation="$root.actorRelationMultiple"
                              :relation-types="$root.actorRelationTypes"
                            ></relation-card>
                          </div>

                          <div style="min-width: 0;">
                              <v-textarea outlined v-model="editedItem.comments" :rules="[rules.required]" :label="translations.comments_"></v-textarea>
                          </div>

                          <div style="min-width: 0;">
                            <v-select item-title="tr" item-value="en" :items="statusItems" class="mx-2" v-model="editedItem.status" :label="translations.status_"></v-select>
                            <div v-if="canRestrictView && !editedItem.id">
                              <v-select
                                  :color="editedItem.roles?.length ? 'error' : 'blue darken-1'"
                                  :prepend-icon="editedItem.roles?.length ? 'mdi-lock' : 'mdi-lock-open'"
                                  chips
                                  :disabled="unrestricted"
                                  item-title="name"
                                  return-object
                                  :items="allowedRoles"
                                  multiple
                                  v-model="editedItem.roles"
                                  :label="translations.restrictToAccessGroups_"
                                  :rules="
                                    !unrestricted ? [validationRules.required(translations.accessGroupsRequired_)] : []
                                  "
                                  clearable
                              ></v-select>
                              <v-checkbox color="error" @change="unrestricted ? editedItem.roles = [] : null" class="mx-2" :label="translations.noAccessAccessGroups_" v-model="unrestricted"> </v-checkbox>
                            </div>
                          </div>
                      </div>
                  </v-card-text>
              </v-sheet>
          </v-card>
      </v-form>
    </v-dialog>

    `,
});

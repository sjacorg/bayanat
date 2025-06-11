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

const ShortActorDialog = Vue.defineComponent({
  components: {
    'tinymce-editor': Editor,
  },
  props: {
    canRestrictView: {
      type: Boolean,
      default: false,
    },
    disabledFields: {
      type: Object,
      default: () => {},
    },
    advFeatures: {
      type: Boolean,
      default: false,
    },
    rules: {
      type: Object,
      default: () => {},
    },
    tinyConfig: {
      type: Object,
      default: () => {},
    },
    editedItem: {
      type: Object,
      default: () => defaultActorData,
    },
    open: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['update:open', 'update:editedItem', 'close'],
  data: () => ({
    valid: false,
    unrestricted: false,
    translations: window.translations,
    tab: 0,
    profileModes: [
      { id: 1, title: "{{ _('Normal')}}", fields: ['source'] }, // Normal Profile
      { id: 2, title: "{{ _('Main')}}", fields: [] }, // Main Profile
      { id: 3, title: "{{ _('Missing Person')}}", fields: ['source', 'mp'] }, // Missing Person Profile
    ],
    defaultItem: defaultActorData,
    saving: false,
  }),
  computed: {
    formTitle() {
      return this.editedItem?.id ? this.translations.editActor_ : this.translations.newActor_;
    },
    nameRule() {
      return [this.editedItem.name || this.editedItem.name_ar ? (v) => true : this.rules.required];
    },
    firstNameRule() {
      return [
        this.editedItem.first_name || this.editedItem.first_name_ar
          ? (v) => true
          : this.rules.required,
      ];
    },
    lastNameRule() {
      return [
        this.editedItem.last_name || this.editedItem.last_name_ar
          ? (v) => true
          : this.rules.required,
      ];
    },

    accessRule() {
      return [
        this.unrestricted || this.editedItem.roles?.length
          ? (v) => true
          : (v) => "{{ _('Access Group(s) are required unless unresticted.')}}",
      ];
    },
    integerRule() {
      return [
        (value) => {
          if (value === null || value === undefined || value === '') return true;
          if (/^\d+$/.test(value)) return true;

          return "{{ _('Please enter a valid number.') }}";
        },
      ];
    },
  },
  methods: {
    modeName(modeId) {
      return this.profileModes.find((x) => x.id == modeId).title;
    },

    deleteProfile(index) {
      if (confirm("{{ _('Are you sure you want to delete this profile?')}}")) {
        if (this.editedItem.actor_profiles.length > 1) {
          this.editedItem.actor_profiles.splice(index, 1);
        } else {
          console.log('Cannot delete the last remaining profile.');
        }
      }
    },

    shouldDisplayField(mode, fieldName) {
      return this.profileModes.find((x) => x.id === mode).fields.includes(fieldName);
    },

    createProfile(profileMode) {
      if (profileMode.id === 2 && this.hasMainProfile) {
        this.showSnack("{{ _('Main profile already exists.')}}");
        return;
      }

      this.profileModeDropdown = false;
      this.editedItem.actor_profiles.push({
        mode: profileMode.id,
      });
      this.tab = this.editedItem.actor_profiles.length - 1;
    },

    duplicateProfile(index) {
      // Check if the profile being duplicated is a main profile and if another main profile exists
      if (this.editedItem.actor_profiles[index].mode === 2 && this.hasMainProfile) {
        this.showSnack('A main profile already exists, cannot create another main profile.');
        return;
      }

      const profileToDuplicate = this.editedItem.actor_profiles[index];
      const newProfile = { ...profileToDuplicate };

      // reset the id of the new profile
      newProfile.id = null;

      // Check if the profile being duplicated is a main profile and if another main profile exists
      if (profileToDuplicate.mode === 2 && this.hasMainProfile) {
        this.showSnack(
          "{{ _('A main profile already exists. Cannot duplicate another main profile.')}}",
        );
        return;
      }

      newProfile.originid = null;
      newProfile.source_link = null;
      newProfile.source_link_type = null;

      // Append the new profile to the actor_profiles array
      this.editedItem.actor_profiles.push(newProfile);
      this.tab = this.editedItem.actor_profiles.length - 1;
    },

    getValidationRules(profile) {
      if (profile.source_link != null) {
        return 'url';
      } else {
        return '';
      }
    },
    confirmClose() {
      if (confirm(translations.confirm_)) {
        this.close();
      }
    },
    close() {
      this.$emit('update:open', false);
      setTimeout(() => {
        this.$emit('update:editedItem', Object.assign({}, this.defaultItem));
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
      if (this.editedItem.id) {
        //update record
        axios
          .put(`/admin/api/actor/${this.editedItem.id}`, {
            item: this.editedItem,
          })
          .then((response) => {
            this.showSnack(response.data);
            this.refresh();
            this.close();
          })
          .catch((err) => {
            console.error(err.response?.data);
            this.showSnack(handleRequestError(err));
            this.saving = false;
          });
      } else {
        //create new record
        axios
          .post('/admin/api/actor/', {
            item: this.editedItem,
          })
          .then((response) => {
            this.items.push(this.editedItem);
            this.showSnack(response.data);
            this.refresh();
            this.close();
          })
          .catch((err) => {
            console.error(err.response?.data);
            this.showSnack(handleRequestError(err));
            this.saving = false;
          });
      }
    },
  },
  template: /*html*/ `
  <vue-win-box v-if="open" ref="wbRef" :options="{ index: 3000, class: ['no-full'] }" @close="$emit('update:open', !open)">
    <template #title>
        <div>{{ formTitle }}</div>
    </template>
    <template #prepend-controls>
        <v-btn @click="validateForm" :disabled="saving" :loading="saving" variant="elevated" class="mx-2" density="compact">
            {{ translations.saveActor_ }}
        </v-btn>
    </template>
    <template #default>
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
                                    :rules="firstNameRule"
                                />
                            </div>
                            <div style="min-width: 0;">
                                <dual-field v-model:original="editedItem.middle_name" v-model:translation="editedItem.middle_name_ar" :label-original="translations.middleName_" :label-translation="translations.middleNameAr_"></dual-field>
                            </div>
                            <div style="min-width: 0;">
                                <dual-field
                                    v-model:original="editedItem.last_name"
                                    v-model:translation="editedItem.last_name_ar"
                                    :label-original="translations.lastName_"
                                    :label-translation="translations.lastNameAr_"
                                    :allow-unknown="true"
                                    :rules="lastNameRule"
                                ></dual-field>
                            </div>
                            <div style="min-width: 0;">
                                <dual-field v-model:original="editedItem.nickname" v-model:translation="editedItem.nickname_ar" :label-original="translations.nickname_" :label-translation="translations.nicknameAr_"></dual-field>
                            </div>

                            <div style="min-width: 0;">
                                <dual-field v-model:original="editedItem.father_name" v-model:translation="editedItem.father_name_ar" :label-original="translations.fathersName_" :label-translation="translations.fathersNameAr_"></dual-field>
                            </div>

                            <div style="min-width: 0;">
                                <dual-field v-model:original="editedItem.mother_name" v-model:translation="editedItem.mother_name_ar" :label-original="translations.mothersName_" :label-translation="translations.mothersNameAr_"></dual-field>
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
                                                <v-card variant="text" class="d-flex align-center">
                                                    <v-text-field class="mx-2" variant="outlined" v-model="profile.originid" :disabled="profile.originidDisabled" :label="translations.originId_"></v-text-field>
                                                </v-card>
                                            </v-card-text>

                                            <v-card-text>
                                                <div class="text-subtitle-2 pa-1">{{ translations.description_ }}</div>
                                                <tinymce-editor :key="index" :init="tinyConfig" v-model="profile.description"></tinymce-editor>
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

                            <div style="min-width: 0;">
                                <v-textarea outlined v-model="editedItem.comments" :rules="[rules.required]" :label="translations.comments_"></v-textarea>
                            </div>

                            <div style="min-width: 0;">
                              <v-select :disabled="disabledFields?.status" item-title="tr" item-value="en" :items="statusItems" class="mx-2" v-model="editedItem.status" :label="translations.status_"></v-select>
                            </div>
                            <div v-if="canRestrictView && !editedItem.id" style="min-width: 0;">
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
                                  :rules="accessRule"
                                  clearable
                              ></v-select>
                              <v-checkbox color="error" @change="unrestricted ? editedItem.roles = [] : null" class="mx-2" :label="translations.noAccessAccessGroups_" v-model="unrestricted"> </v-checkbox>
                            </div>
                        </div>
                    </v-card-text>
                </v-sheet>
            </v-card>
        </v-form>
    </template>
</vue-win-box>

    `,
});

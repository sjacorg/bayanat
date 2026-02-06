const getDefaultActorData = () => ({
  description: '',
  type: 'Person',
  // related events
  events: [],
  // related media
  medias: [],
  // related actors
  actor_relations: [],
  id_number: [],
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
});

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
    eventParams: {
      type: Object,
      default: () => ({}),
    },
    prefillData: {
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
    open: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['update:open', 'close', 'createActor'],
  data: () => ({
    editedItem: getDefaultActorData(),
    relation: {
      probability: null,
      related_as: null,
      comment: null,
    },
    idNumberTypes: [],
    valid: false,
    unrestricted: false,
    translations: window.translations,
    validationRules: validationRules,
    tab: 0,
    profileModes: [
      { id: 1, title: window.translations.normal_, fields: ['source'] }, // Normal Profile
      { id: 2, title: window.translations.main_, fields: [] }, // Main Profile
      { id: 3, title: window.translations.missingPerson_, fields: ['source', 'mp'] }, // Missing Person Profile
    ],
    saving: false,
    serverErrors: {},
  }),
  computed: {
    formTitle() {
      return this.editedItem?.id ? this.translations.editActor_ : this.translations.newActor_;
    },
    simpleIdNumberValue() {
      return this.editedItem.id_number?.map(idNumber => ({ type: idNumber?.type?.id ? idNumber?.type?.id?.toString() : idNumber?.type, number: idNumber?.number?.toString() }));
    },
  },
  mounted() {
    this.fetchIdNumberTypes();
  },
  methods: {
    fetchIdNumberTypes() {
      // If already loaded the exit
      if (this.idNumberTypes.length) return;

      // Fetch and cache IDNumberType data for ID number display and editing
      axios
        .get('/admin/api/idnumbertypes/')
        .then((res) => {
          this.idNumberTypes = res.data.items || [];
        })
        .catch((err) => {
          this.idNumberTypes = [];
          console.error('Error fetching id number types:', err);
          this.$root.showSnack(handleRequestError(err));
        });
    },

    updateIdNumber(updatedItems) {
      this.editedItem.id_number = updatedItems.map((item) => ({
        type: this.idNumberTypes.find((type) => Number(type.id) === Number(item.type)),
        number: item.number,
      }));
    },
    shouldDisplayField(mode, fieldName) {
      return this.profileModes.find((x) => x.id === mode).fields.includes(fieldName);
    },
    confirmClose() {
      if (confirm(translations.areYouSure_)) {
        this.close();
      }
    },
    close() {
      this.$emit('update:open', false);
      setTimeout(() => {
        this.editedItem = getDefaultActorData();
        this.unrestricted = false;
        this.saving = false;
        this.serverErrors = {}
      }, 300);
    },
    validateForm() {
      this.$refs.form.validate().then(({ valid, errors }) => {
        if (valid) {
          this.save();
        } else {
          this.$root.showSnack(translations.pleaseReviewFormForErrors_);
          scrollToFirstError();
        }
      });
    },
    save() {
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

      const payload = {
        ...this.editedItem,
        id_number: this.simpleIdNumberValue
    }

      //create new record
      axios
        .post('/admin/api/actor/', {
          item: payload,
        })
        .then((response) => {
          if (response?.data?.item?.id) {
            this.$emit('createActor', {
              item: { ...response.data.item },
              relationData: {
                probability: this.relation.probability,
                related_as: this.relation.related_as,
                comment: this.relation.comment,
              },
            });
          }
          this.$root.showSnack(response.data.message);
          this.close();
        })
        .catch((err) => {
          console.error(err.response?.data);
          this.$root.showSnack(handleRequestError(err));
          this.serverErrors = err.response?.data?.errors || {};
          this.$nextTick(() => scrollToFirstError());
        }).finally(() => {
          this.saving = false;
        });
    },
  },
  watch: {
    parentItem: {
      handler(newParentItem) {
        const actorProfile = this.editedItem.actor_profiles.find(Boolean);
      
        this.editedItem = {
          ...this.editedItem,
          ...this.prefillData,
          comments: `First Data Analysis from Bulletin ${newParentItem.id ? '#' + newParentItem.id : ''}`,
          status: 'Human Created',
          roles: newParentItem.roles,
        };
      
        if (actorProfile) {
          actorProfile.sources = newParentItem?.sources ?? [];
        }
      },
      deep: true,
      immediate: true,
    },
  },
  template: /*html*/ `
    <v-dialog
        v-if="open"
        :modelValue="open"
        v-bind="$root.rightDialogProps"
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
          <v-card class="overflow-hidden position-static">
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
                                  v-bind="$root.serverErrorPropsForDualField(serverErrors, 'item.first_name', 'item.first_name_ar')"
                              />
                          </div>
                          <div style="min-width: 0;">
                              <dual-field
                                v-model:original="editedItem.middle_name"
                                v-model:translation="editedItem.middle_name_ar"
                                :label-original="translations.middleName_"
                                :label-translation="translations.middleNameAr_"
                                :rules="[validationRules.maxLength(255)]"
                                v-bind="$root.serverErrorPropsForDualField(serverErrors, 'item.middle_name', 'item.middle_name_ar')"
                              ></dual-field>
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
                                  v-bind="$root.serverErrorPropsForDualField(serverErrors, 'item.last_name', 'item.last_name_ar')"
                              ></dual-field>
                          </div>
                          <div style="min-width: 0;">
                            <dual-field
                              v-model:original="editedItem.nickname"
                              v-model:translation="editedItem.nickname_ar"
                              :label-original="translations.nickname_"
                              :label-translation="translations.nicknameAr_"
                              :rules="[
                                  validationRules.maxLength(255),
                              ]"
                              v-bind="$root.serverErrorPropsForDualField(serverErrors, 'item.nickname', 'item.nickname_ar')"
                            ></dual-field>
                          </div>
                          <div style="min-width: 0;">
                            <dual-field
                              v-model:original="editedItem.father_name"
                              v-model:translation="editedItem.father_name_ar"
                              :label-original="translations.fathersName_"
                              :label-translation="translations.fathersNameAr_"
                              :rules="[
                                  validationRules.maxLength(255),
                              ]"
                              v-bind="$root.serverErrorPropsForDualField(serverErrors, 'item.father_name', 'item.father_name_ar')"
                            ></dual-field>
                          </div>
                          <div style="min-width: 0;">
                            <dual-field
                              v-model:original="editedItem.mother_name"
                              v-model:translation="editedItem.mother_name_ar"
                              :label-original="translations.mothersName_"
                              :label-translation="translations.mothersNameAr_"
                              :rules="[
                                  validationRules.maxLength(255),
                              ]"
                              v-bind="$root.serverErrorPropsForDualField(serverErrors, 'item.mother_name', 'item.mother_name_ar')"
                            ></dual-field>
                          </div>

                          <div style="min-width: 0;">
                              <v-select :items="translations.actorSex" item-title="tr" item-value="en" v-model="editedItem.sex" clearable :label="translations.sex_"></v-select>
                          </div>

                          <div style="min-width: 0;">
                            <v-select
                              :items="translations.actorAge"
                              item-title="tr"
                              item-value="en"
                              v-model="editedItem.age"
                              clearable
                              :label="translations.minorAdult_"
                            ></v-select>
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
                            <dual-field
                              v-model:original="editedItem.occupation"
                              v-model:translation="editedItem.occupation_ar"
                              :label-original="translations.occupation_"
                              :label-translation="translations.occupationAr_"
                              :rules="[
                                  validationRules.maxLength(255),
                              ]"
                              v-bind="$root.serverErrorPropsForDualField(serverErrors, 'item.occupation', 'item.occupation_ar')"
                            ></dual-field>
                          </div>
                          <div style="min-width: 0;">
                            <dual-field
                              v-model:original="editedItem.position"
                              v-model:translation="editedItem.position_ar"
                              :label-original="translations.position_"
                              :label-translation="translations.positionAr_"
                              :rules="[
                                  validationRules.maxLength(255),
                              ]"
                              v-bind="$root.serverErrorPropsForDualField(serverErrors, 'item.position', 'item.position_ar')"
                            ></dual-field>
                          </div>
                          <div style="min-width: 0;">
                            <v-autocomplete
                              :items="translations.actorFamilyStatuses"
                              clearable
                              item-title="tr"
                              item-value="en"
                              v-model="editedItem.family_status"
                              :label="translations.familyStatus_"
                            ></v-autocomplete>
                          </div>
                          <div style="min-width: 0;">
                            <v-text-field :label="translations.noOfChildren_"
                              v-model="editedItem.no_children"
                              :rules="[validationRules.integer()]"
                              v-bind="$root.serverErrorPropsForField(serverErrors, 'item.no_children')"
                            ></v-text-field>
                          </div>
                          <div style="min-width: 0;">
                            <search-field
                              v-model="editedItem.nationalities"
                              api="/admin/api/countries/"
                              item-title="title"
                              item-value="title"
                              :multiple="true"
                              clearable
                              :label="translations.nationalities_"
                            ></search-field>
                          </div>

                          <div style="min-width: 0;">
                              <v-combobox chips multiple v-model="editedItem.tags" :label="translations.tags_"></v-combobox>
                          </div>

                          <div style="grid-column: 1 / -1; min-width: 0;">
                              <!-- ID Numbers Management -->
                              <id-number-dynamic-field
                                  :model-value="simpleIdNumberValue"
                                  @update:model-value="updateIdNumber"
                                  :id-number-types="idNumberTypes"
                              ></id-number-dynamic-field>
                          </div>


                          <div v-if="editedItem.actor_profiles?.length" style="grid-column: 1 / -1; min-width: 0;">
                              <v-window class="w-100 border" v-model="tab">
                                  <v-window-item v-for="(profile, index) in editedItem.actor_profiles" :key="index">
                                      <v-card class="pa-3" variant="text">
                                          <!-- Source Link -->
                                          <v-card-text v-if="shouldDisplayField(profile.mode, 'source')">
                                              <v-text-field class="mx-2" variant="outlined" v-model="profile.originid" :disabled="profile.originidDisabled" :label="translations.originId_"
                                                v-bind="$root.serverErrorPropsForField(serverErrors, 'item.actor_profiles.'+index+'.originid')"
                                            ></v-text-field>
                                          </v-card-text>

                                          <v-card-text>
                                            <div class="text-subtitle-2 pa-1 ">{{ translations.description_ }}</div>
                                            <tinymce-editor
                                                    :key="index"
                                                    :init="$root.tinyConfig"
                                                    v-model="profile.description"
                                            ></tinymce-editor>
                                          </v-card-text>

                                          <v-card-text>
                                              <!-- Sources -->
                                              <search-field v-model="profile.sources" api="/admin/api/sources/" item-title="title" item-value="id" :multiple="true" :label="translations.sources_"></search-field>
                                          </v-card-text>

                                          <v-card-text>
                                              <!-- Labels -->
                                              <search-field v-model="profile.labels" api="/admin/api/labels/" item-title="title" item-value="id" :multiple="true" :show-copy-icon="advFeatures" :label="translations.labels_"></search-field>
                                          </v-card-text>

                                          <v-card-text>
                                              <!-- Verified Labels -->
                                              <search-field
                                                    v-model="profile.ver_labels"
                                                    api="/admin/api/labels/"
                                                    :query-params="{ fltr: 'verified', typ: 'for_actor' }"
                                                    item-title="title"
                                                    item-value="id"
                                                    :multiple="true"
                                                    :show-copy-icon="advFeatures"
                                                    :label="translations.verifiedLabels_"
                                            ></search-field>
                                          </v-card-text>
                                      </v-card>
                                  </v-window-item>
                              </v-window>
                          </div>

                          <div style="grid-column: 1 / -1; min-width: 0;">
                            <events-section :edited-item="editedItem" :dialog-props="$root.rightContainedDialogProps" :show-copy-icon="advFeatures" :event-params="eventParams"></events-section>
                          </div>

                          <div style="grid-column: 1 / -1; min-width: 0;">
                            <relation-editor-card
                              v-model:relation="relation"
                              :multi-relation="$root.actorRelationMultiple"
                              :relation-types="$root.actorRelationTypes"
                              :title="translations.relationshipWithBulletin_(parentItem.id ? '#' + parentItem.id : '')"
                            >
                              <template #append>
                                <v-alert type="info" variant="tonal" density="compact" :text="translations.relationshipBetweenActorAndBulletinWillBeCreated_"></v-alert>
                              </template>
                            </relation-editor-card>
                          </div>

                          <div style="min-width: 0;">
                              <v-textarea outlined v-model="editedItem.comments" :rules="[validationRules.required()]" :label="translations.comments_"></v-textarea>
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

window.ShortActorDialog = ShortActorDialog;
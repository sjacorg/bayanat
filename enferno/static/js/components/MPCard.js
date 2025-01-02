const MPCard = Vue.defineComponent({
  props: {
    profileId: Number,
  },
  data: function () {
    return {
      translations: window.translations,
      loading: false,
      mp: null,
      show: false,
    };
  },

  watch: {},

  computed: {
    showDPS() {
      if (this.mp) {
        if (this.mp.saw_name || this.mp.saw_address || this.mp.saw_email || this.mp.saw_phone) {
          return true;
        }
      }
      return false;
    },
  },

  mounted: function () {},

  methods: {
    loadData() {
      this.loading = true;
      axios
        .get(`/admin/api/actormp/${this.profileId}`)
        .then((response) => {
          this.mp = response.data;
          this.show = true;
        })
        .catch((error) => {
          console.log(error.body.data);
        })
        .finally(() => {
          this.loading = false;
        });
    },
  },
  template: `
          <v-card class=" ma-2" >
          <v-toolbar density="compact">
            <v-toolbar-title>
            <v-btn variant="text" prepend-icon="mdi-chart-donut" :loading="loading" @click="loadData"  >
              
              {{ translations.missingPerson_ }}
            </v-btn>
              </v-toolbar-title>
          </v-toolbar>
          <template v-if="mp">
            <v-card-text>

              <mp-field :field="this.mp.last_address" :title="translations.lastAddress_"></mp-field>

              <mp-field :field="this.mp.marriage_history" :title="translations.marriageHistory_"></mp-field>

              <mp-field :field="this.mp.bio_children" :title="translations.bioChildren_"></mp-field>

              <mp-field :field="this.mp.pregnant_at_disappearance" :title="translations.pregnantAtDisappearance_"></mp-field>
              <mp-field :field="this.mp.months_pregnant" :title="translations.mpAtDisappearance_"></mp-field>
              <mp-field :field="this.mp.missing_relatives" :title="translations.missingRelatives_"></mp-field>
              <v-card v-if="showDPS" color="yellow lighten-5" class="my-2" outlined>
                <v-card-text>
                  <h3 class="subtitle-2 mb-2 black--text">{{ translations.detailsPersonSawLast_ }}</h3>
                  <mp-field :field="this.mp.saw_name" :title="translations.name_"></mp-field>
                  <mp-field :field="this.mp.saw_address" :title="translations.address_"></mp-field>
                  <mp-field :field="this.mp.saw_phone" :title="translations.phone_"></mp-field>
                  <mp-field :field="this.mp.saw_email" :title="translations.email_"></mp-field>
                </v-card-text>
              </v-card>
              <mp-field :field="this.mp.seen_in_detention" :type="1" :title="translations.seenInDetentionCenter_"></mp-field>
              <mp-field :field="this.mp.injured" :type="1" :title="translations.injuredDisappearance_"></mp-field>
              <mp-field :field="this.mp.known_dead" :type="1" :title="translations.knownDead_"></mp-field>
              <mp-field :field="this.mp.death_details" :title="translations.deathDetails_"></mp-field>
              <mp-field :field="this.mp.personal_items" :title="translations.personalItemsEg_"></mp-field>
              <mp-field :field="this.mp.height" :title="translations.height_"></mp-field>
              <mp-field :field="this.mp.weight" :title="translations.weight_"></mp-field>
              <mp-field :field="this.mp._physique" :title="translations.physique_"></mp-field>
              <mp-field :field="this.mp._hair_loss" :title="translations.hairloss_"></mp-field>
              <mp-field :field="this.mp._hair_type" :title="translations.hairtype_"></mp-field>
              <mp-field :field="this.mp._hair_length" :title="translations.hairlength_"></mp-field>
              <mp-field :field="this.mp._hair_color" :title="translations.haircolor_"></mp-field>
              <mp-field :field="this.mp._facial_hair" :title="translations.facialhair_"></mp-field>
              <mp-field :field="this.mp.posture" :title="translations.postureNotes_"></mp-field>
              <mp-field :type="1" :field="this.mp.skin_markings" :title="translations.skinMarkings_"></mp-field>
              <mp-field :field="this.mp._handedness" :title="translations.handedness_"></mp-field>
              <mp-field :field="this.mp.glasses" :title="translations.glasses_"></mp-field>
              <mp-field :field="this.mp._eye_color" :title="translations.eyecolor_"></mp-field>
              <mp-field :field="this.mp.dist_char_con" :title="translations.characteristicsCongenital_"></mp-field>
              <mp-field :field="this.mp.dist_char_acq" :title="translations.characteristicsAcquired_"></mp-field>
              <mp-field :field="this.mp.physical_habits" :title="translations.physicalHabits_"></mp-field>
              <mp-field :field="this.mp.other" :title="translations.otherComments_"></mp-field>
              <mp-field :field="this.mp.phys_name_contact" :title="translations.physiciansContact_"></mp-field>
              <mp-field :field="this.mp.injuries" :title="translations.fracturesInjuries_"></mp-field>
              <mp-field :field="this.mp.implants" :title="translations.implants_ "></mp-field>
              <mp-field :field="this.mp.malforms" :title="translations.congenitalMalformations_"></mp-field>
              <mp-field :field="this.mp.pain" :title="translations.painAilments_"></mp-field>
              <mp-field :field="this.mp.other_conditions" :title="translations.otherMedicalConditions_"></mp-field>
              <mp-field :field="this.mp.accidents" :title="translations.accidents_"></mp-field>
              <mp-field :field="this.mp.pres_drugs" :title="translations.prescriptionDrugsTaken_"></mp-field>
              <mp-field :field="this.mp.smoker" :title="translations.smoker_"></mp-field>
              <mp-field :field="this.mp.dental_record" :title="translations.isDentalRecord_"></mp-field>
              <mp-field :field="this.mp.dentist_info" :title="translations.DentistContact_"></mp-field>
              <mp-field :field="this.mp.teeth_features" :title="translations.teethFeatures_"></mp-field>
              <mp-field :field="this.mp.dental_problems" :title="translations.dentalProblems_"></mp-field>
              <mp-field :field="this.mp.dental_treatments" :title="translations.dentalTreatments_"></mp-field>
              <mp-field :field="this.mp.dental_habits" :title="translations.dentalHabits_"></mp-field>
              <mp-field :field="this.mp._case_status" :title="translations.caseStatus_"></mp-field>
              <mp-field :type="2" :field="this.mp.reporters" :title="translations.reporters_"></mp-field>
              <mp-field :field="this.mp.identified_by" :title="translations.identifiedBy"></mp-field>
              <mp-field :field="this.mp.family_notified" :title="translations.familyNotified_"></mp-field>
              <mp-field :field="this.mp.reburial_location" :title="translations.reburialLocation_"></mp-field>
      

            </v-card-text>

          </template>

          </v-card>

        `,
});

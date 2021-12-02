Vue.component("mp-card", {
    props: {
        actorId: Number,
        i18n: Object

    },
    data: function () {
        return {
            loading: false,
            mp: null,
            show: false
        };
    },

    watch: {},

    computed : {
      showDPS(){
          if (this.mp) {
              if (this.mp.saw_name || this.mp.saw_address || this.mp.saw_email || this.mp.saw_phone){
                  return true
              }
          }
          return false;

      }
    },


    mounted: function () {


    },

    methods: {
        loadData() {

            this.loading = true;
            axios.get(`/admin/api/actormp/${this.actorId}`).then((response) => {

                this.mp = response.data;
                this.show = true;


            }).catch(error => {
                console.log(error.body.data)

            }).finally(() => {
                this.loading = false;
            });

        }

    },
    template:
        `
          <v-card class="pa-1 ma-3 elevation-1" color="yellow lighten-4">
          <v-card-title class="subtitle-2">
            <v-btn :loading="loading" @click="loadData" small color="yellow lighten-3 black--text" elevation="0">
              <v-icon color="deep-orange" left>mdi-chart-donut</v-icon>
              {{ i18n.missingPerson_ }}
            </v-btn>
          </v-card-title>
          <template v-if="mp">
            <v-card-text>

              <mp-field :field="this.mp.last_address" :title="i18n.lastAddress_"></mp-field>

              <mp-field :field="this.mp.marriage_history" :title="i18n.marriageHistory_"></mp-field>

              <mp-field :field="this.mp.bio_children" :title="i18n.bioChildren_"></mp-field>

              <mp-field :field="this.mp.pregnant_at_disappearance" :title="i18n.pregnantAtDisappearance_"></mp-field>
              <mp-field :field="this.mp.months_pregnant" :title="i18n.mpAtDisappearance_"></mp-field>
              <mp-field :field="this.mp.missing_relatives" :title="i18n.missingRelatives_"></mp-field>
              <v-card v-if="showDPS" color="yellow lighten-5" class="my-2" outlined>
                <v-card-text >
                  <h3 class="subtitle-2 mb-2 black--text">{{ i18n.detailsPersonSawLast_ }}</h3>
                  <mp-field :field="this.mp.saw_name" :title="i18n.name_"></mp-field>
                  <mp-field :field="this.mp.saw_address" :title="i18n.address_"></mp-field>
                  <mp-field :field="this.mp.saw_phone" :title="i18n.phone_"></mp-field>
                  <mp-field :field="this.mp.saw_email" :title="i18n.email_"></mp-field>
                </v-card-text>
              </v-card>
              <mp-field :field="this.mp.seen_in_detention" type="1" :title="i18n.seenInDetentionCenter_"></mp-field>
              <mp-field :field="this.mp.injured" type="1" :title="i18n.injuredDisappearance_"></mp-field>
              <mp-field :field="this.mp.known_dead" type="1" :title="i18n.knownDead_"></mp-field>
              <mp-field :field="this.mp.death_details" :title="i18n.deathDetails_"></mp-field>
              <mp-field :field="this.mp.personal_items" :title="i18n.personalItemsEg_"></mp-field>
              <mp-field :field="this.mp.height" :title="i18n.height_"></mp-field>
              <mp-field :field="this.mp.weight" :title="i18n.weight_"></mp-field>
              <mp-field :field="this.mp._physique" :title="i18n.physique_"></mp-field>
              <mp-field :field="this.mp._hair_loss" :title="i18n.hairloss_"></mp-field>
              <mp-field :field="this.mp._hair_type" :title="i18n.hairtype_"></mp-field>
              <mp-field :field="this.mp._hair_length" :title="i18n.hairlength_"></mp-field>
              <mp-field :field="this.mp._hair_color" :title="i18n.haircolor_"></mp-field>
              <mp-field :field="this.mp._facial_hair" :title="i18n.facialhair_"></mp-field>
              <mp-field :field="this.mp.posture" :title="i18n.postureNotes_"></mp-field>
              <mp-field type="1" :field="this.mp.skin_markings" :title="i18n.skinMarkings_"></mp-field>
              <mp-field :field="this.mp._handedness" :title="i18n.handness_"></mp-field>
              <mp-field :field="this.mp.glasses" :title="i18n.glasses_"></mp-field>
              <mp-field :field="this.mp._eye_color" :title="i18n.eyecolor_"></mp-field>
              <mp-field :field="this.mp.dist_char_con" :title="i18n.characteristicsCongenital_"></mp-field>
              <mp-field :field="this.mp.dist_char_acq" :title="i18n.characteristicsAcquired_"></mp-field>
              <mp-field :field="this.mp.physical_habits" :title="i18n.physicalHabits_"></mp-field>
              <mp-field :field="this.mp.other" :title="i18n.otherComments_"></mp-field>
              <mp-field :field="this.mp.phys_name_contact" :title="i18n.physiciansContact_"></mp-field>
              <mp-field :field="this.mp.injuries" :title="i18n.fracturesInjuries_"></mp-field>
              <mp-field :field="this.mp.implants" :title="i18n.implants_ "></mp-field>
              <mp-field :field="this.mp.malforms" :title="i18n.congenitalMalformations_"></mp-field>
              <mp-field :field="this.mp.pain" :title="i18n.painAilments_"></mp-field>
              <mp-field :field="this.mp.other_conditions" :title="i18n.otherMedicalConditions_"></mp-field>
              <mp-field :field="this.mp.accidents" :title="i18n.accidents_"></mp-field>
              <mp-field :field="this.mp.pres_drugs" :title="i18n.prescriptionDrugsTaken_"></mp-field>
              <mp-field :field="this.mp.smoker" :title="i18n.smoker_"></mp-field>
              <mp-field :field="this.mp.dental_record" :title="i18n.isDentalRecord_"></mp-field>
              <mp-field :field="this.mp.dentist_info" :title="i18n.DentistContact_"></mp-field>
              <mp-field :field="this.mp.teeth_features" :title="i18n.teethFeatures_"></mp-field>
              <mp-field :field="this.mp.dental_problems" :title="i18n.dentalProblems_"></mp-field>
              <mp-field :field="this.mp.dental_treatments" :title="i18n.dentalTreatmetns_"></mp-field>
              <mp-field :field="this.mp.dental_habits" :title="i18n.dentalHabits_"></mp-field>
              <mp-field :field="this.mp._case_status" :title="i18n.caseStatus_"></mp-field>
              <mp-field :i18n="i18n" type="2" :field="this.mp.reporters" :title="i18n.reporters_"></mp-field>
              <mp-field :field="this.mp.identified_by" :title="i18n.identifiedBy"></mp-field>
              <mp-field :field="this.mp.family_notified" :title="i18n.familyNotified_"></mp-field>
              <mp-field :field="this.mp.reburial_location" :title="i18n.reburialLocation_"></mp-field>
      

            </v-card-text>

          </template>

          </v-card>

        `,
});

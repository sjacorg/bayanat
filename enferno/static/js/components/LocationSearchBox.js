const LocationSearchBox = Vue.defineComponent({
  props: {
    modelValue: {
      type: Object,
      required: true,
    },
  },

  data: () => {
    return {
      translations: window.translations,
      q: {},
    };
  },
  watch: {
    q: {
      handler(newVal) {
        this.$emit("update:modelValue", newVal);
      },
      deep: true,
    },

    modelValue : function (newVal, oldVal) {
      if (newVal !== oldVal) {
        this.q = newVal;
      }
    },
  },
  created() {
    this.q = this.modelValue;
  },

  template: `
      <v-sheet>
      <v-card>
        <v-toolbar :title="translations.searchLocations_" > 
          
          
          <template #append>
            <v-btn icon="mdi-close" @click="$emit('close')">
            
          </v-btn>
            
          </template>
        </v-toolbar>


        <v-container class="fluid">
          <v-row>
            <v-col>


              <v-text-field
                  v-model="q.title"
                  :label="translations.title_"
                  clearable
                  @keydown.enter="$emit('search',q)"
              ></v-text-field>

              <v-text-field
                  v-model="q.tsv"
                  :label="translations.description_"
                  clearable
              ></v-text-field>

              
              <v-sheet color="grey lighten-4" class="ma-4"> 
                <geo-map
                    class="flex-grow-1"
                    v-model="q.latlng"
                    :map-height="200"
                    :radius-controls="true" />
              </v-sheet>


              <search-field
                  v-model="q.location_type"
                  api="/admin/api/location-types/"
                  item-title="title"
                  item-value="id"
                  :multiple="false"
                  :label="translations.locationType_">
              </search-field>


              <search-field
                  api="/admin/api/location-admin-levels/"
                  item-title="title"
                  item-value="id"
                  v-model="q.admin_level"
                  :multiple="false"
                  :label="translations.adminLevel_">
              </search-field>


              <search-field
                  v-model="q.country"
                  api="/admin/api/countries/"
                  item-title="title"
                  item-value="id"
                  :multiple="false"
                  clearable
                  :label="translations.country_"
              ></search-field>

              <div class="d-flex align-center">
                <v-combobox
                    v-model="q.tags"
                    label="Tags"
                    multiple
                    deletable-chips
                    small-chips
                    clearable
                ></v-combobox>

                <v-checkbox :label="translations.any_" dense v-model="q.optags" color="primary" small
                            class="mx-3"></v-checkbox>

              </div>


            </v-col>
          </v-row>


        </v-container>


      </v-card>
      <v-card tile class="text-center  search-toolbar" elevation="10" color="grey lighten-5">
        <v-card-text>
          <v-spacer></v-spacer>
          <v-btn @click="q={}" text>{{ translations.clearSearch_ }}</v-btn>

          <v-btn @click="$emit('search',q)" color="primary">{{ translations.search_ }}</v-btn>
          <v-spacer></v-spacer>
        </v-card-text>

      </v-card>

      </v-sheet>
    `,
});

window.LocationSearchBox = LocationSearchBox;

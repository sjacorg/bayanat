Vue.component('location-search-box', {
    props: {
        value: {
            type: Object, required: true
        },
        i18n: {
            type: Object
        }
    },

    data: () => {
        return {
            q: {},


        }
    }, watch: {

        q: {
            handler(newVal) {
                this.$emit('input', newVal)
            }, deep: true
        },

        value: function (newVal, oldVal) {

            if (newVal !== oldVal) {
                this.q = newVal;
            }
        }

    }, created() {
        this.q = this.value;

    },

    template: `
      <v-sheet>
      <v-card class="pa-4">
        <v-card-title>
          Search Locations
          <v-spacer></v-spacer>
          <v-btn fab text @click="$emit('close')">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>


        <v-container class="fluid">
          <v-row>
            <v-col>


              <v-text-field
                  v-model="q.title"
                  label="Title"
                  clearable
                  @keydown.enter="$emit('search',q)"
              ></v-text-field>

              <v-text-field
                  v-model="q.tsv"
                  label="Description"
                  clearable
              ></v-text-field>

              
              <v-sheet color="grey lighten-4" class="ma-4"> 
                <geo-map
                    class="flex-grow-1"
                    v-model="q.latlng"
                    map-height="200"
                    radius-controls="true" />
              </v-sheet>


              <search-field
                  v-model="q.location_type"
                  api="/admin/api/location-types/"
                  item-text="title"
                  item-value="id"

                  :return-object="false"
                  :multiple="false"
                  label="Location Type">
              </search-field>


              <search-field
                  api="/admin/api/location-admin-levels/"
                  item-text="title"
                  item-value="id"

                  v-model="q.admin_level"

                  :return-object="false"
                  :multiple="false"
                  label="Admin level">
              </search-field>


              <search-field
                  v-model="q.country"
                  api="/admin/api/countries/"
                  item-text="title"
                  item-value="title"
                  :multiple="false"
                  :return-object="false"
                  clearable
                  label="Country"
                  
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

                <v-checkbox :label="i18n.any_" dense v-model="q.optags" color="primary" small
                            class="mx-3"></v-checkbox>

              </div>


            </v-col>
          </v-row>


        </v-container>


      </v-card>
      <v-card tile class="text-center  search-toolbar" elevation="10" color="grey lighten-5">
        <v-card-text>
          <v-spacer></v-spacer>
          <v-btn @click="q={}" text>{{ i18n.clearSearch_ }}</v-btn>

          <v-btn @click="$emit('search',q)" color="primary">{{ i18n.search_ }}</v-btn>
          <v-spacer></v-spacer>
        </v-card-text>

      </v-card>

      </v-sheet>
    `

})
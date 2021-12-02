Vue.component("drop-field", {
    props: {
        caption: String,
        samples: [],
        value: []
    },
    data: function () {
        return {
            colmap: this.value || [],
            disabled: false,
        };
    },

    watch: {

        value (val){
           this.colmap = val || [];

        },
        colmap : {
            handler: 'refresh',
            deep: true
        }

    },

    mounted: function () {
         //this.broadcast();
    },

    methods: {
         refresh() {

            // restrict to one item
            if (this.colmap.length > 0){
                this.disabled = true
            }
            else {
                this.disabled = false;
            }
            this.broadcast();
        },


        broadcast() {
            this.$emit('input', this.colmap);
        },
        removeMe(i){
        let item = this.colmap.splice(i,1);
        this.$root.returnToStack(item)
        },
    },
    template: `

      <v-sheet class="d-flex stripe-1 align-center  ma-2 pa-2" elevation="0">
      <h5 class="d-caption">{{ caption }}</h5>
      <div class="drop">
        <draggable
            :disabled="disabled"
            tag="div"
            v-model="colmap"

            @change="refresh"
            class="drag-area list-group "
            :group="{ name: 'columns', pull: false, put: true, ghostClass: 'ghost', animation: 100 }"
        >

          <v-chip small v-for="(item,i) in colmap"
                  
                  @click:close="removeMe(i)"

                  class="ma-1 list-group-item" dark :key="i" close color="primary">
            
              {{item }}
          </v-chip>


        </draggable>
      </div>
 <slot name="extra"></slot>
      </v-sheet>

    `,
});

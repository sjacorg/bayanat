Vue.component("address-field", {
    props: {
        value: {}
    },
    data: function () {
        return {
            address: {}
        };
    },

    watch: {
        value: function (val) {
            //console.log('called')
            this.address = val;
        },
        address: {
            handler: 'refresh',
            deep: true
        }

    },

    mounted: function () {


    },

    methods: {
        refresh() {
            this.$emit('input', this.address);

        }
    },
    template: `
      <div>
      <v-text-field label="Address Line 1" v-model="address.line1"></v-text-field>
      <v-text-field label="Address Line 2" v-model="address.line2"></v-text-field>
      <div class="d-flex">
        <v-text-field label="Street" v-model="address.street"></v-text-field>
        <v-text-field label="Street No" v-model="address.streetno"></v-text-field>

      </div>
      <div class="d-flex">
        <v-text-field label="City" v-model="address.city"></v-text-field>
        <v-text-field label="Country" v-model="address.country"></v-text-field>
      </div>
      </div>

    `,
});

const AddressField = Vue.defineComponent({
  props: {
    value: {},
  },
  data: function () {
    return {
      address: {},
      translations: window.translations
    };
  },

  watch: {
    value: function (val) {
      //console.log('called')
      this.address = val;
    },
    address: {
      handler: 'refresh',
      deep: true,
    },
  },

  mounted: function () {},

  methods: {
    refresh() {
      this.$emit('input', this.address);
    },
  },
  template: `
      <div>
      <v-text-field :label="translations.addrLine1" v-model="address.line1"></v-text-field>
      <v-text-field :label="translations.addrLine2" v-model="address.line2"></v-text-field>
      <div class="d-flex">
        <v-text-field :label="translations.street_" v-model="address.street"></v-text-field>
        <v-text-field :label="translations.streetNo_" v-model="address.streetno"></v-text-field>

      </div>
      <div class="d-flex">
        <v-text-field :label="translations.city_" v-model="address.city"></v-text-field>
        <v-text-field :label="translations.country_" v-model="address.country"></v-text-field>
      </div>
      </div>

    `,
});

window.Address = Address;

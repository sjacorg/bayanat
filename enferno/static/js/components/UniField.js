const UniField = Vue.defineComponent({
  props: {
    caption: String,
    english: String,
    arabic: String,
  },
  data: function () {
    return {
      sw: true,
    };
  },

  mounted: function () {},

  methods: {},
  template: `

    <v-list v-if="english || arabic"  variant="plain" class="mx-2 my-1 pa-2 d-flex align-center flex-grow-1">
      
      <v-list-item :title="caption"  v-if="sw">
        <v-sheet class="text-body-2" >{{english}}</v-sheet>
        <template #append v-if="english && arabic">
            <v-btn variant="text" size="x-small" icon="mdi-web" @click="sw= !sw"></v-btn>
        </template>
      </v-list-item>
      <v-list-item  :title="caption"  v-else>
        <v-sheet class="text-body-2"> {{arabic}}</v-sheet>
        <template #append v-if="english && arabic">
            <v-btn variant="text" size="x-small" icon="mdi-web" @click="sw= !sw"></v-btn>
        </template>
      
      </v-list-item>

    </v-list>
  `,
});

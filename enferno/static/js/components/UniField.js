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
      
      <v-list-item lines="one" :title="caption" :subtitle="english" v-if="sw">
        <template #append v-if="english && arabic">
            <v-btn variant="text" size="x-small" icon="mdi-web" @click="sw= !sw"></v-btn>
        </template>
      </v-list-item>
      <v-list-item lines="one" :title="caption" :subtitle="arabic" v-else>
        
        <template #append v-if="english && arabic">
            <v-btn variant="text" size="x-small" icon="mdi-web" @click="sw= !sw"></v-btn>
        </template>
      
      </v-list-item>

    </v-list>
  `,
});

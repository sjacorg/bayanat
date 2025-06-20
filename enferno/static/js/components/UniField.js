const UniField = Vue.defineComponent({
  props: {
    caption: String,
    english: String,
    arabic: String,
    disableSpacing: Boolean
  },
  data() {
    return {
      sw: this.english ? true : false,
    };
  },
  template: `
    <v-list v-if="english || arabic"  variant="plain" :class="['d-flex align-center flex-grow-1', { 'mx-2 my-1 pa-2': !disableSpacing }]">
      <template v-if="english && arabic">
        <v-list-item :title="caption" density="compact" :class="{ 'px-0': disableSpacing }">
          <v-sheet class="text-body-2">{{ sw ? english : arabic }}</v-sheet>
          <template #append>
              <v-btn variant="text" size="x-small" icon="mdi-web" @click="sw= !sw"></v-btn>
          </template>
        </v-list-item>
      </template>

      <template v-else>
        <v-list-item :title="caption" density="compact" :class="{ 'px-0': disableSpacing }">
          <v-sheet class="text-body-2">{{ english || arabic }}</v-sheet>
        </v-list-item>
      </template>
    </v-list>
  `,
});

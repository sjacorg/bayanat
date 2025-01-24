const DiffRenderer = Vue.defineComponent({
    props: ['diff'],
    template: `
    <v-sheet border color="background" class="change-item pa-2 my-1 d-flex flex-column ga-4 overflow-auto" max-height="471px">
        <div v-for="change in diff">
            <div class="body-2 text--black">{{ change.label }}</div>
            <div v-html="change.diff"></div>
        </div>
    </v-sheet>
    `,
});

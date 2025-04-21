const DiffRenderer = Vue.defineComponent({
    props: ['diff'],
    template: `
    <v-sheet border color="background" class="change-item pa-2 my-1 d-flex flex-column ga-4 overflow-auto" max-height="471px" min-width="530px">
        <div v-html="diff"></div>
    </v-sheet>
    `,
});

const DiffRenderer = Vue.defineComponent({
    props: ['diff'],
    template: `
    <v-sheet border color="background" class="change-item pa-2 my-1 d-flex flex-column ga-4 overflow-auto w-100" max-height="471px">
        <div v-html="diff"></div>
    </v-sheet>
    `,
});

export default DiffRenderer;
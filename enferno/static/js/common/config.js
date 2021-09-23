// global vuetify config object passed to most pages of the system
const vuetify = new Vuetify({
    //rtl: __lang__ &&__lang__ == 'ar',
    theme: {
        // read dark mode from settings (passed from python)
        dark: __settings__.dark,

        themes: {
            light: {
                primary: "#439d92",
                secondary: "#b0bec5",
                accent: "#8c9eff",
                third: "#8aa396",
                fourth: "#b5c1aa",
                fifth: "#dde0c6",
                yv: "#F6932B",
                ov: "#FCB001",
                rv: "#910C0A",
                gv: "#9ECCC3",
                pv: "#295651",
                error: "#b71c1c"
            },
            // adjust colors for dark mode based on color name
            dark: {
                white: "#222",
                grey: {
                    base: "#999",
                    lighten2: "#777",
                    lighten4: "#222",
                    lighten3: "#232323",
                    lighten5: "#333"
                },
                'blue-grey': {
                    base: "#222",
                    lighten5: "#444"
                },
                black : {
                    base: '#ddd',
                    '--text': '#ddd'
                },
                yellow: {
                    lighten5: '#24240f'
                },
                primary: '#09a7a6',
                gv :{
                    darken2: "#019985"
                },
                lime: {
                    lighten5 : "#303030"

                },
                teal:  {
                    lighten5: "#008080"
                }




            }
        }
    },
    icons: {
        iconfont: "mdi"
    }
});

// other UI config settings
const drawer = null;
const dialog = false;

// pass custom delimiters to avoid conflict between vue and jinja delimiters syntax
const delimiters = ["${", "}"];

// define side nav items

const sideNav = [
    {
        icon: "mdi-library-books",
        text: "Bulletins",
        href: "/admin/bulletins/"
    },

    {
        icon: "mdi-account-multiple",
        text: "Actors",
        href: "/admin/actors/"
    },
    {
        icon: "mdi-hazard-lights",
        text: "Incidents",
        href: "/admin/bulletins/"
    },

    {
        icon: "mdi-folder-marker",
        text: "Locations",
        href: "/admin/locations/"
    },
    {
        icon: "mdi-google-circles-extended",
        text: "Sources",
        href: "/admin/sources/"
    },

    {
        icon: "mdi-label",
        text: "Labels",
        href: "/admin/labels/"
    },
    {
        icon: "mdi-calendar-range",
        text: "Event Types",
        href: "/admin/eventtypes/"
    },

    {
        icon: "mdi-account-multiple",
        text: "Users Management",
        href: "/admin/users/"
    },

    {
        icon: "mdi-shield-lock",
        text: "Groups & Permissions",
        href: "/admin/roles/"
    },

    {
        icon: "mdi-settings",
        text: "Settings"
    },

    {
        icon: "mdi-help",
        text: "Help"
    }
];

const geoMapDefaultCenter = {lat: 33.510414,lng: 36.278336};

// items per page for data tables
// adjust items per page dynamically based on screen hight

let itemsPerPageOptions = [10, 50, 100, 250, 500];
if (window.innerHeight > 1000){
    itemsPerPageOptions = [50,100,250,500]
}
if (window.innerHeight > 1500){
    itemsPerPageOptions = [100,250,500]
}


// debounce function calls, helps avoid excessive calls to the server when using auto-complete fields
const debounce = (fn, time) => {
    let timeout;

    return function () {
        const functionCall = () => fn.apply(this, arguments);
        clearTimeout(timeout);
        timeout = setTimeout(functionCall, time);
    };
};

// register components for vee validate
Vue.component("validation-provider", VeeValidate.ValidationProvider);
Vue.component("validation-observer", VeeValidate.ValidationObserver);

//register leaflet map components
Vue.component('l-map', window.Vue2Leaflet.LMap);
Vue.component('l-tile-layer',window.Vue2Leaflet.LTileLayer);
Vue.component('l-marker', window.Vue2Leaflet.LMarker);
Vue.component('l-circle-marker', window.Vue2Leaflet.LCircleMarker);
Vue.component('l-popup', window.Vue2Leaflet.LPopup);
Vue.component('l-icon', window.Vue2Leaflet.LIcon);
const mapsApiEndpoint = window.__MAPS_API_ENDPOINT__;

// define custom regexp URL validator for source links
VeeValidate.extend("url", {
    validate: (str) => {

        const pattern = new RegExp(
            "^(https?:\\/\\/){1,1}" + // protocol
            "((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,}|" + // domain name
            "((\\d{1,3}\\.){3}\\d{1,3}))" + // OR ip (v4) address
            "(\\:\\d+)?(\\/[-a-z\\d%_.~+]*)*" + // port and path
            "(\\?[;&a-z\\d%_.~+=-]*)?" + // query string
            "(\\#[-a-z\\d_]*)?$",
            "i"
        ); // fragment locator

        const pathReg = new RegExp(
            "^\\/([A-z0-9-_+]+\\/)*([A-z0-9]+(.*))$", "i"
        )
        return !!pattern.test(str) || str == 'NA' || !!pathReg.test(str);
    },
});

// change to true for dev mode
Vue.config.devtools = false;

//global axios error handler - can be used to define global exception handling on ajax failures
axios.interceptors.response.use(function (response) {
    // Do something with response data
    return response;
}, function (error) {
    // Do something with response error
    if (error.response) {
        //console.log(error.response.status)

        if (error.response.status == 403) {
            //location.href="/logout";
        }
    }
    return Promise.reject(error);
});

//  in-page router for bulleints/actors/incidents pages
const router = new VueRouter({
    // mode: 'history',
    routes: [
        {path: '/admin/bulletins/:id'},
        {path: '/admin/actors/:id'},
        {path: '/admin/incidents/:id'}
    ]
});

// Rich text configurations for tinymce editor
var tinyConfig = {
    plugins: ["link autolink directionality fullscreen code"],
    paste_data_images: true,


    block_formats: "Paragraph=p; Header 1=h1; Header 2=h2; Header 3=h3",
    branding: false,
    default_link_target: "_blank",

    menubar: false,
    toolbar:
        "undo redo | styleselect | bold italic | link image | alignleft aligncenter alignright | ltr rtl | removeformat |  code | fullscreen",

    style_formats: [
        {title: "Heading 2", format: "h2"},
        {title: "Heading 3", format: "h3"},
        {title: "Paragraph", format: "p"}
    ]
};

// adjust rich text editor theme based on mode
if (__settings__.dark) {
    tinyConfig.skin =  "oxide-dark";
    tinyConfig.content_css ="dark";
}

// define static data contants for different fields
let i = translations;
var mediaCats = [i.generic_, i.humans_, i.signsText_ ];
var probs = [i.maybe_, i.likely_, i.certain_];
var btobRelateAs = [i.duplicate_, i.other_, i.partOfSeries_, i.sameObject_, i.samePerson_,i.potentiallyDuplicate_, i.potentiallyRelated_];
var itobRelateAs = [i.default_];
var itoiRelateAs = [i.default_];
var statuses = [
    i.machineCreated_,
    i.humanCreated_,
    i.updated_,
    i.peerReviewed_,
    i.finalized_,
    i.seniorReviewed_,
    i.machineUpdated_,
    i.assigned_,
    i.secondPeerReview_,
    i.revisited_,
    i.seniorUpdated_,
    i.peerReviewAssigned_
];

var geoLocationTypes = [
    i.default_,
    i.establishment_,
    i.park_,

]

var countries = [
i.afghanistan_,
i.albania_,
i.algeria_,
i.andorra_,
i.angola_,
i.argentina_,
i.armenia_,
i.aruba_,
i.australia_,
i.austria_,
i.azerbaijan_,
i.bahrain_,
i.bangladesh_,
i.barbados_,
i.belarus_,
i.belgium_,
i.belize_,
i.benin_,
i.bhutan_,
i.bosniaandherzegovina_,
i.botswana_,
i.brazil_,
i.brunei_,
i.bulgaria_,
i.burkinafaso_,
i.burma_,
i.burundi_,
i.cambodia_,
i.cameroon_,
i.canada_,
i.centralafricanrepublic_,
i.chad_,
i.chile_,
i.china_,
i.colombia_,
i.comoros_,
i.democraticrepublicofthecongo_,
i.republicofthecongo_,
i.cotedivoire_,
i.croatia_,
i.cuba_,
i.cyprus_,
i.czechia_,
i.denmark_,
i.djibouti_,
i.dominica_,
i.dominicanrepublic_,
i.egypt_,
i.eritrea_,
i.estonia_,
i.ethiopia_,
i.finland_,
i.france_,
i.gabon_,
i.gambia_,
i.georgia_,
i.germany_,
i.ghana_,
i.greece_,
i.guinea_,
i.guineabissau_,
i.guyana_,
i.haiti_,
i.honduras_,
i.hungary_,
i.iceland_,
i.india_,
i.indonesia_,
i.iran_,
i.iraq_,
i.ireland_,
i.israel_,
i.italy_,
i.jamaica_,
i.japan_,
i.jordan_,
i.kazakhstan_,
i.kenya_,
i.kosovo_,
i.kuwait_,
i.kyrgyzstan_,
i.laos_,
i.latvia_,
i.lebanon_,
i.liberia_,
i.libya_,
i.liechtenstein_,
i.lithuania_,
i.luxembourg_,
i.macedonia_,
i.madagascar_,
i.malawi_,
i.malaysia_,
i.mali_,
i.malta_,
i.mauritania_,
i.mauritius_,
i.micronesia_,
i.moldova_,
i.monaco_,
i.mongolia_,
i.montenegro_,
i.morocco_,
i.mozambique_,
i.namibia_,
i.nauru_,
i.nepal_,
i.netherlands_,
i.newzealand_,
i.nicaragua_,
i.niger_,
i.nigeria_,
i.northkorea_,
i.norway_,
i.oman_,
i.pakistan_,
i.palestine_,
i.panama_,
i.philippines_,
i.poland_,
i.portugal_,
i.qatar_,
i.romania_,
i.russia_,
i.rwanda_,
i.saudiarabia_,
i.senegal_,
i.serbia_,
i.seychelles_,
i.sierraleone_,
i.slovakia_,
i.slovenia_,
i.somalia_,
i.southafrica_,
i.southsudan_,
i.spain_,
i.srilanka_,
i.sudan_,
i.swaziland_,
i.sweden_,
i.switzerland_,
i.syria_,
i.taiwan_,
i.tajikistan_,
i.tanzania_,
i.thailand_,
i.togo_,
i.tonga_,
i.trinidadandtobago_,
i.tunisia_,
i.turkey_,
i.turkmenistan_,
i.tuvalu_,
i.uganda_,
i.ukraine_,
i.unitedarabemirates_,
i.unitedkingdom_,
i.unitedstates_,
i.uruguay_,
i.uzbekistan_,
i.venezuela_,
i.vietnam_,
i.yemen_,
i.zambia_,
i.zimbabwe_,
i.other_,
]

// helper protoype functions

// removes an item from the array based on its id
Array.prototype.removeById = function (id) {
    for (let i = 0; i < this.length; i++) {
        if (this[i].id == id) {
            this.splice(i, 1);
            i--;
        }
    }
    return this;
};

Array.prototype.toURLParams = function (varName) {
    const pairs = this.map(x => {
        return `${varName}=${x}`
    })
    return pairs.join('&');
}

String.prototype.getFilename = function () {
    return this.substring(this.lastIndexOf('/') + 1).replace(/[\#\?].*$/, '').replace(/\.[^/.]+$/, "");

}

String.prototype.formatName = function () {
    let firstlast = this.split(' ');
    return firstlast[0].substr(0, 1).toUpperCase() + '.' + firstlast[1];

}
// global image viewer
var viewer = new ImageViewer.FullScreenViewer();


// Advanced system search
var dateWithin = [
    {'text': i.oneDay_, value: '1d',},
    {'text': i.twoDays_, value: '2d',},
    {'text': i.threeDays_, value: '3d',},
    {'text': i.fourDays_ , value: '4d',},
    {'text': i.fiveDays_, value: '5d',},
    {'text': i.sixDays_, value: '6d',},
    {'text': i.sevenDays_, value: '7d',},
    {'text': i.oneMonth_, value: '30d',},
    {'text': i.threeMonths_, value: '90d',},
    {'text': i.sixMonths_, value: '180d',},
    {'text': i.oneYear_, value: '365d',},
];


// Experimental (make dialogs draggable)

(function () {
    // make vuetify dialogs movable
    const d = {};
    document.addEventListener("mousedown", e => {
        const closestDialog = e.target.closest(".v-dialog.v-dialog--active");
        if (
            e.button === 0 &&
            closestDialog != null &&
            e.target.classList.contains("v-card__title")
        ) {
            // element which can be used to move element
            d.el = closestDialog; // element which should be moved
            d.mouseStartX = e.clientX;
            d.mouseStartY = e.clientY;
            d.elStartX = d.el.getBoundingClientRect().left;
            d.elStartY = d.el.getBoundingClientRect().top;
            d.el.style.position = "fixed";
            d.el.style.margin = 0;
            d.oldTransition = d.el.style.transition;
            d.el.style.transition = "none";
        }
    });
    document.addEventListener("mousemove", e => {
        if (d.el === undefined) return;
        d.el.style.left =
            Math.min(
                Math.max(d.elStartX + e.clientX - d.mouseStartX, 0),
                window.innerWidth - d.el.getBoundingClientRect().width
            ) + "px";
        d.el.style.top =
            Math.min(
                Math.max(d.elStartY + e.clientY - d.mouseStartY, 0),
                window.innerHeight - d.el.getBoundingClientRect().height
            ) + "px";
    });
    document.addEventListener("mouseup", () => {
        if (d.el === undefined) return;
        d.el.style.transition = d.oldTransition;
        d.el = undefined;
    });
    setInterval(() => {
        // prevent out of bounds
        const dialog = document.querySelector(".v-dialog.v-dialog--active");
        if (dialog === null) return;
        dialog.style.left =
            Math.min(
                parseInt(dialog.style.left),
                window.innerWidth - dialog.getBoundingClientRect().width
            ) + "px";
        dialog.style.top =
            Math.min(
                parseInt(dialog.style.top),
                window.innerHeight - dialog.getBoundingClientRect().height
            ) + "px";
    }, 100);
})();


// videojs config settings  - prevent plugin from sending data
window.HELP_IMPROVE_VIDEOJS = false;
// Video player playback rates
const VIDEO_RATES = [0.25, 0.5, 1, 1.5, 2, 4]


// media screenshots helper method
dataUriToBlob = function (dataURI) {
    // convert base64/URLEncoded data component to raw binary data held in a string
    var byteString;
    if (dataURI.split(',')[0].indexOf('base64') >= 0)
        byteString = atob(dataURI.split(',')[1]);
    else
        byteString = unescape(dataURI.split(',')[1]);

    // separate out the mime component
    var mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];

    // write the bytes of the string to a typed array
    var ia = new Uint8Array(byteString.length);
    for (var i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }

    return new Blob([ia], {type: mimeString});
}

const VID_EXT = ["webm", "mkv", "flv", "vob", "ogv", "ogg", "rrc", "gifv", "mng", "mov", "avi", "qt", "wmv", "yuv", "rm", "asf", "amv", "mp4", "m4p", "m4v", "mpg", "mp2", "mpeg", "mpe", "mpv", "m4v", "svi", "3gp", "3g2", "mxf", "roq", "nsv", "flv", "f4v", "f4p", "f4a", "f4b",  "mts", "lvr", "m2ts"]
const ETL_EXTENSIONS = ["jpg", "jpeg","png","gif","doc","docx","pdf", "txt", "ttf"].concat(VID_EXT)
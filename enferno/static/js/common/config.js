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

// items per page for data tables
const itemsPerPageOptions = [10, 50, 100, 250, 500];

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
var mediaCats = ["Generic", "Humans", "Signs/Text"];
var probs = ["Maybe", "Likely", "Certain"];
var btobRelateAs = ["Duplicate", "Other", "Part of a Series", "Same Object", "Same Person"];
var itobRelateAs = ["default"];
var itoiRelateAs = ["Default"];
var statuses = [
    "Machine Created",
    "Human Created",
    "Updated",
    "Peer Reviewed",
    "Finalized",
    "Senior Reviewed",
    "Machine Updated",
    "Assigned",
    "Second Peer Review",
    "Revisited",
    "Senior Updated",
    "Peer Review Assigned"
];

var countries = [
    "Afghanistan",
    "Albania",
    "Algeria",
    "Andorra",
    "Angola",
    "Argentina",
    "Armenia",
    "Aruba",
    "Australia",
    "Austria",
    "Azerbaijan",
    "Bahrain",
    "Bangladesh",
    "Barbados",
    "Belarus",
    "Belgium",
    "Belize",
    "Benin",
    "Bhutan",
    "Bosnia and Herzegovina",
    "Botswana",
    "Brazil",
    "Brunei",
    "Bulgaria",
    "Burkina Faso",
    "Burma",
    "Burundi",
    "Cambodia",
    "Cameroon",
    "Canada",
    "Central African Republic",
    "Chad",
    "Chile",
    "China",
    "Colombia",
    "Comoros",
    "Congo, Democratic Republic of the",
    "Congo, Republic of the",
    "Cote d'Ivoire",
    "Croatia",
    "Cuba",
    "Cyprus",
    "Czechia",
    "Denmark",
    "Djibouti",
    "Dominica",
    "Dominican Republic",
    "Egypt",
    "Eritrea",
    "Estonia",
    "Ethiopia",
    "Finland",
    "France",
    "Gabon",
    "Gambia, The",
    "Georgia",
    "Germany",
    "Ghana",
    "Greece",
    "Guinea",
    "Guinea-Bissau",
    "Guyana",
    "Haiti",
    "Honduras",
    "Hungary",
    "Iceland",
    "India",
    "Indonesia",
    "Iran",
    "Iraq",
    "Ireland",
    "Israel",
    "Italy",
    "Jamaica",
    "Japan",
    "Jordan",
    "Kazakhstan",
    "Kenya",
    "Kosovo",
    "Kuwait",
    "Kyrgyzstan",
    "Laos",
    "Latvia",
    "Lebanon",
    "Liberia",
    "Libya",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Macedonia",
    "Madagascar",
    "Malawi",
    "Malaysia",
    "Mali",
    "Malta",
    "Mauritania",
    "Mauritius",
    "Micronesia",
    "Moldova",
    "Monaco",
    "Mongolia",
    "Montenegro",
    "Morocco",
    "Mozambique",
    "Namibia",
    "Nauru",
    "Nepal",
    "Netherlands",
    "New Zealand",
    "Nicaragua",
    "Niger",
    "Nigeria",
    "North Korea",
    "Norway",
    "Oman",
    "Pakistan",
    "Palestine",
    "Panama",
    "Philippines",
    "Poland",
    "Portugal",
    "Qatar",
    "Romania",
    "Russia",
    "Rwanda",
    "Saudi Arabia",
    "Senegal",
    "Serbia",
    "Seychelles",
    "Sierra Leone",
    "Slovakia",
    "Slovenia",
    "Somalia",
    "South Africa",
    "South Sudan",
    "Spain",
    "Sri Lanka",
    "Sudan",
    "Swaziland",
    "Sweden",
    "Switzerland",
    "Syria",
    "Taiwan",
    "Tajikistan",
    "Tanzania",
    "Thailand",
    "Togo",
    "Tonga",
    "Trinidad and Tobago",
    "Tunisia",
    "Turkey",
    "Turkmenistan",
    "Tuvalu",
    "Uganda",
    "Ukraine",
    "United Arab Emirates",
    "United Kingdom",
    "United States",
    "Uruguay",
    "Uzbekistan",
    "Venezuela",
    "Vietnam",
    "Yemen",
    "Zambia",
    "Zimbabwe",
    "Other",
];

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
    {'text': '1 day', value: '1d',},
    {'text': '2 day', value: '2d',},
    {'text': '3 days', value: '3d',},
    {'text': '4 days', value: '4d',},
    {'text': '5 days', value: '5d',},
    {'text': '6 days', value: '6d',},
    {'text': '7 days', value: '7d',},
    {'text': '1 Month', value: '30d',},
    {'text': '3 Months', value: '90d',},
    {'text': '6 Months', value: '180d',},
    {'text': '1 Year', value: '365d',},
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
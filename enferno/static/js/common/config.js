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
                black: {
                    base: '#ddd',
                    '--text': '#ddd'
                },
                yellow: {
                    lighten5: '#24240f'
                },
                primary: '#09a7a6',
                gv: {
                    darken2: "#019985"
                },
                lime: {
                    lighten5: "#303030"

                },
                teal: {
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
        text: "Groups Management",
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
// adjust items per page dynamically based on screen hight


if (window.innerHeight > 1000) {
    itemsPerPageOptions = [50, 100, 250, 500]
}
if (window.innerHeight > 1500) {
    itemsPerPageOptions = [100, 250, 500]
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
Vue.component('l-tile-layer', window.Vue2Leaflet.LTileLayer);
Vue.component('l-marker', window.Vue2Leaflet.LMarker);
Vue.component('l-circle-marker', window.Vue2Leaflet.LCircleMarker);
Vue.component('l-popup', window.Vue2Leaflet.LPopup);
Vue.component('l-icon', window.Vue2Leaflet.LIcon);
Vue.component('l-control', window.Vue2Leaflet.LControl);

Vue.use(VueTippy);

const mapsApiEndpoint = window.__MAPS_API_ENDPOINT__;


/*
// Hybrid
{
    url: 'http://{s}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}',
    subdomains:['mt0','mt1','mt2','mt3']
}

// Terrain
{
    url: 'http://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
    subdomains: ['mt0','mt1','mt2','mt3']
}


 */

// define custom regexp URL validator for source links
VeeValidate.extend("url", {
    validate: (str) => {

        const pattern = new RegExp("^(https?:\\/\\/)((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,}|((\\d{1,3}\\.){3}\\d{1,3}))(:\\d+)?(\\/[\\w%.~+-]*)*(\\?[;&\\w%.~+=-]*)?(#\\w*)?$",
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

function handleRequestError(error) {
    if (error.response) {
        return error.response.data || 'An error occurred.';
    } else if (error.request) {
        return 'No response from server. Contact an admin.';
    } else {
        return 'Request failed. Check your network connection.';
    }
};

//  in-page router for bulletins/actors/incidents pages
const router = new VueRouter({
    mode: 'history',
    routes: [

        {path: '/admin/bulletins/:id'},
        {path: '/admin/actors/:id'},
        {path: '/admin/incidents/:id'},
        {path: '/admin/locations/:id'},
        {path: '/export/dashboard/:id'}
    ]
});

// Rich text configurations for tinymce editor
var tinyConfig = {
    plugins: ["link autolink directionality fullscreen lists table searchreplace image"],
    toolbar_mode: 'sliding',
    images_upload_url: '/admin/api/inline/upload',
    images_upload_base_path: '/admin/api/serve/inline/',
    images_reuse_filename: true,

    block_formats: "Paragraph=p; Header 1=h1; Header 2=h2; Header 3=h3",
    branding: true,
    default_link_target: "_blank",
    table_grid: false,
    menubar: false,
    toolbar:
        "undo redo | styleselect | bold italic underline strikethrough backcolor | outdent indent | numlist bullist | link image | align | ltr rtl | table | removeformat | searchreplace | fullscreen",
    toolbar_groups: {
        align: {
            icon: 'aligncenter',
            tooltip: 'Align',
            items: 'alignleft aligncenter alignright alignjustify'
        }
    },
    table_toolbar: 'tableprops tabledelete | tableinsertrowbefore tableinsertrowafter tabledeleterow | tableinsertcolbefore tableinsertcolafter tabledeletecol',

    style_formats: [
        {title: "Heading 1", format: "h1"},
        {title: "Heading 2", format: "h2"},
        {title: "Heading 3", format: "h3"},
        {title: "Paragraph", format: "p"}
    ]
    ,
    cleanup: true
};

// adjust rich text editor theme based on mode
if (__settings__.dark) {
    tinyConfig.skin = "oxide-dark";
    tinyConfig.content_css = "dark";
}

// define static data contants for different fields

let i = translations;
// var mediaCats = [i.generic_, i.humans_, i.signsText_];
// var probs = [i.maybe_, i.likely_, i.certain_];
// var btobRelateAs = [i.duplicate_, i.other_, i.partOfSeries_, i.sameObject_, i.samePerson_, i.potentiallyDuplicate_, i.potentiallyRelated_];
// var itobRelateAs = [i.default_];
// var itoiRelateAs = [i.default_];
// var statuses = i.statuses_;

// var geoLocationTypes = [
//     i.default_,
//     i.school_,
//     i.religious_,
//     i.militaryStructure_,
//     i.infrastructure_,
//     i.medical_,

// ]

// var countries = i.countries_

// helper prototype functions

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
String.prototype.trunc = function (n) {
    return this.substr(0, n - 1) + (this.length > n ? '&hellip;' : '');
};


//helper method to translate front-end strings using an array of translation objects (constructed in i18n.jinja2)
function translate_status(str) {
    // const needle = i.statuses_.filter(x => x.en == str).pop();
    // if (needle.tr) {
    //     return needle.tr;
    // } else {
    //     return needle.en;
    // }
    return str
}

String.prototype.toHHMMSS = function () {
    var sec_num = parseInt(this, 10); // don't forget the second param
    var hours = Math.floor(sec_num / 3600);
    var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
    var seconds = sec_num - (hours * 3600) - (minutes * 60);

    if (hours < 10) {
        hours = "0" + hours;
    }
    if (minutes < 10) {
        minutes = "0" + minutes;
    }
    if (seconds < 10) {
        seconds = "0" + seconds;
    }
    return hours + ':' + minutes + ':' + seconds;
}


String.prototype.formatName = function () {
    let firstlast = this.split(' ');
    return firstlast[0].substr(0, 1).toUpperCase() + '.' + firstlast[1];

}

// relationship information helper

function extractValuesById(dataList, idList, valueKey) {

    // handle null related_as case
    if (idList === null) {
        return [];
    }

    return dataList
        .filter(item => idList.includes(item.id))
        .map(item => item[valueKey]);
}


// global helper methods for geolocations

var aggregateBulletinLocations = function (bulletin) {
    let locations = [];
    // aggregate locations, add a color identifier
    if (bulletin.locations?.length) {
        let locs = bulletin.locations.filter(x => x.lat && x.lng);
        locs.map(x => {
            x.color = '#00a1f1';
            x.parentId = bulletin.id;
            return x
        });
        locations = locations.concat(locs);


    }

    // geolocations
    if (bulletin.geoLocations?.length) {
        bulletin.geoLocations.map((x, i) => {
            x.number = i + 1;
            x.color = '#ffbb00';
            x.parentId = bulletin.id;
            x.full_string = x.title;
            return x
        });
        locations = locations.concat(bulletin.geoLocations);
    }
    // event locations
    if (bulletin.events && bulletin.events.length) {
        const eventLocations = prepareEventLocations(bulletin.id, bulletin.events);
        locations = locations.concat(eventLocations);
    }

    return locations;
}

var aggregateActorLocations = function (actor) {
    let locations = [];

    const addLocation = (place, type) => {
        if (place && place.latlng) {
            place.type = type;
            place.color = '#00a1f1';
            place.parentId = actor.id;
            place.lat = place.latlng.lat;
            place.lng = place.latlng.lng;
            locations.push(place);
        }
    };

    addLocation(actor.birth_place, 'Birth Place');
    addLocation(actor.residence_place, 'Residence Place');
    addLocation(actor.origin_place, 'Origin Place');

    // event locations
    if (actor.events && actor.events.length) {
        const eventLocations = prepareEventLocations(actor.id, actor.events);
        locations = locations.concat(eventLocations);
    }

    return locations;
}


function prepareEventLocations(parentId, events) {
    let output = events.filter(x => x.location && x.location.latlng);
    // sort events by from/to date and leave null date events at the end
    output.sort((a, b) => {
        const aDate = a.from_date || a.to_date;
        const bDate = b.from_date || b.to_date;

        if (aDate && bDate) {
            return new Date(aDate) - new Date(bDate);
        }
        if (!aDate) {
            return 1;
        }
        if (!bDate) {
            return -1;
        }
    });
    return output.map((x, i) => {
        //attach serial number to events for map reference
        x.location.number = i + 1;
        x.location.title = x.title;
        x.location.type = 'Event';
        x.location.parentId = parentId;
        x.location.color = '#00f166';
        x.location.lat = x.location.latlng.lat;
        x.location.lng = x.location.latlng.lng;
        x.location.zombie = x.from_date === null && x.to_date === null;
        x.location.eventtype = x.eventtype?.title;
        return x.location
    });
}


function parseResponse(dzFile) {
    // helper method to convert xml response to friendly json format
    const response = JSON.parse(dzFile.xhr.response);

    return {

        uuid: dzFile.upload.uuid,
        type: dzFile.type,
        s3url: response.filename,
        filename: response.filename,
        etag: response.etag
    }

}

function getBulletinLocations(ids) {
    promises = []
    ids.forEach(x => {
        promises.push(axios.get(`/admin/api/bulletin/${x}?mode=3`).then(response => {
            return aggregateBulletinLocations(response.data);
        }));
    });
    return Promise.all(promises);
}

var aggregateIncidentLocations = function (incident) {

    let locations = [];

    if (incident.locations && incident.locations.length) {
        let locs = incident.locations.filter(x => x.lat && x.lng);
        locs.map(x => {
            x.color = '#00a1f1';
            return x
        });
        locations = locations.concat(locs);

    }

    // event locations
    if (incident.events && incident.events.length) {
        let eventLocations = incident.events.filter(x => x.location && x.location.lat && x.location.lng).map((x, i) => {
            // exclude locations with null coordinates

            //attach serial number to events for map reference
            x.location.number = i + 1;
            x.location.title = x.title;
            x.location.color = '#00f166';
            return x.location


        });


        locations = locations.concat(eventLocations);
    }
    return locations;

}

// global image viewer
var viewer = new ImageViewer.FullScreenViewer();

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

const VID_EXT = [".webm", ".mkv", ".flv", ".vob", ".ogv", ".ogg", ".rrc", ".gifv", ".mng", ".mov", ".avi", ".qt", ".wmv", ".yuv", ".rm", ".asf", ".amv", ".mp4", ".m4p", ".m4v", ".mpg", ".mp2", ".mpeg", ".mpe", ".mpv", ".m4v", ".svi", ".3gp", ".3g2", ".mxf", ".roq", ".nsv", ".flv", ".f4v", ".f4p", ".f4a", ".f4b", ".mts", ".lvr", ".m2ts"]
const OCR_EXT = [".png", ".jpeg", ".tiff", ".jpg", ".gif", ".webp", ".bmp", ".pnm"]
const ETL_EXTENSIONS = [".gif", ".doc", ".docx", ".pdf", ".txt", ".ttf"].concat(VID_EXT).concat(OCR_EXT)
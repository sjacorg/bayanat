// common validation rules

const validationRules = {
    required: (value) => !!value || 'Required.',
    min: (v) => v.length >= 6 || 'Min 6 characters',
};

// Helper functions
function scrollToElementById(elementId) {
    const element = document.getElementById(elementId)
    element?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
    })
}

// global vuetify config object passed to most pages of the system
const vuetifyConfig = {
    defaults: {
        VTextField: {
            variant: 'outlined'
        },
        VSelect: {
            variant: 'outlined'
        },
        VTextarea: {
            variant: 'outlined'
        },
        VCombobox: {
            variant: 'outlined'

        },
        VChip: {
            size: 'small'
        },
        VDataTableServer: {
            itemsPerPageOptions: window.itemsPerPageOptions,
        },
    },
    theme: {
        defaultTheme: __settings__.dark ? 'dark' : 'light', // Dynamically set based on __settings__.dark
        themes: {
            light: {
                dark: false, // Explicitly set the light theme as not dark
                colors: {
                    primary: '#439d92',
                    secondary: '#b0bec5',
                    accent: '#8c9eff',
                    error: '#b71c1c',
                    // Additional custom colors from your vuetifyConfig light theme
                    third: '#8aa396',
                    fourth: '#b5c1aa',
                    fifth: '#dde0c6',
                    yv: '#F6932B',
                    ov: '#FCB001',
                    rv: '#910C0A',
                    gv: '#9ECCC3',
                    pv: '#295651',
                },
            },
            dark: {
                dark: true, // Explicitly set the dark theme as dark
                colors: {
                    white: '#333', // Adapted to the more complex structure of your dark theme
                    // Adapted to the more complex structure of your dark theme
                    primary: '#09a7a6',
                    grey: '#999', // Only one shade represented for simplicity
                    'blue-grey': '#222', // Base color, assuming primary shade
                    black: '#ddd', // Base color
                    gv: '#019985', // Darken2 shade assumed for simplicity
                    lime: '#303030',
                    teal: '#008080',
                    // You might need to adjust or add additional custom colors here
                },
            },
        },
    },
    // Preserve other configurations outside the theme structure
    icons: {
        iconfont: 'mdi',
    },
};

// other UI config settings
const drawer = true;
const dialog = false;

// pass custom delimiters to avoid conflict between vue and jinja delimiters syntax
const delimiters = ['${', '}'];


// debounce function calls, helps avoid excessive calls to the server when using auto-complete fields
const debounce = (fn, time) => {
    let timeout;

    return function () {
        const functionCall = () => fn.apply(this, arguments);
        clearTimeout(timeout);
        timeout = setTimeout(functionCall, time);
    };
};


//register leaflet map components
const mapsApiEndpoint = window.__MAPS_API_ENDPOINT__;

//global axios error handler - can be used to define global exception handling on ajax failures
axios.interceptors.response.use(
    function (response) {
        // Do something with response data
        return response;
    },
    function (error) {
        const globalRequestErrorEvent = new CustomEvent('global-axios-error', { detail: error });
        document.dispatchEvent(globalRequestErrorEvent);
        // Check for session expiration errors (401 Unauthorized)
        if ([401].includes(error?.response?.status)) {
            const authenticationRequiredEvent = new CustomEvent('authentication-required', { detail: error });
            document.dispatchEvent(authenticationRequiredEvent);
        }
        return Promise.reject(error);
    },
);

function handleRequestError(error) {
    if (error?.response?.data?.response?.errors) {
        return error?.response?.data?.response?.errors?.join('\n') || 'An error occurred.';
    } else if (error?.response?.data?.errors) {
        const errors = error?.response?.data?.errors;
        let message = '';
        for(const field in errors){
            let fieldName = field;
            if (fieldName.startsWith('item.')){
                fieldName = fieldName.substring(5);
            }
            message += `<strong style="color:#b71c1c;">[${!fieldName.includes("__root__") ? fieldName : 'Validation Error'}]:</strong> ${errors[field]}<br/>`;
        }
        return message;
    } else if (error?.response?.data) {
        if (error?.response?.data?.includes('<!DOCTYPE html>')) return 'An error occurred.'
        return error.response.data || 'An error occurred.';
    } else if (error.request) {
        return 'No response from server. Contact an admin.';
    } else if (error?.message) {
        return error.message || 'An error occurred.';
    } else {
        return 'Request failed. Check your network connection.';
    }
}

//  in-page router for bulletins/actors/incidents pages
const {createRouter, createWebHistory, createWebHashHistory} = VueRouter;

const routes = [
    {path: '/', name: 'home', component: Vue.defineComponent({template: ''})},

    {path: '/admin/bulletins/:id', name: 'bulletin', component: Vue.defineComponent({})},
    {path: '/admin/bulletins/', name: 'bulletins', component: Vue.defineComponent({})},
    {path: '/admin/actors/:id', name: 'actor', component: Vue.defineComponent({})},
    {path: '/admin/actors/', name: 'actors', component: Vue.defineComponent({})},
    {path: '/admin/incidents/:id', name: 'incident', component: Vue.defineComponent({})},
    {path: '/admin/incidents/', name: 'incidents', component: Vue.defineComponent({})},
    {path: '/admin/locations/:id', name: 'location', component: Vue.defineComponent({})},
    {path: '/admin/locations/', name: 'locations', component: Vue.defineComponent({})},
    {path: '/admin/activity/', name: 'activity', component: Vue.defineComponent({})},
    {path: '/export/dashboard/:id', name: 'export', component: Vue.defineComponent({})},
    {path: '/export/dashboard/', name: 'exports', component: Vue.defineComponent({})},
    {path: '/import/log/:id', name: 'log', component: Vue.defineComponent({})},
    {path: '/import/log/', name: 'logs', component: Vue.defineComponent({})},
    {path: '/admin/users/:id', name: 'user', component: Vue.defineComponent({})},
    {path: '/admin/users/', name: 'users', component: Vue.defineComponent({})},

];

const router = createRouter({
    history: createWebHistory(),
    routes: routes,
});

// Rich text configurations for tinymce editor
var tinyConfig = {
    license_key: 'gpl',
    plugins: 'link autolink directionality fullscreen lists table searchreplace image',
    toolbar_mode: 'sliding',
    images_upload_url: '/admin/api/inline/upload',
    images_upload_base_path: '/admin/api/serve/inline/',
    images_reuse_filename: true,

    block_formats: 'Paragraph=p; Header 1=h1; Header 2=h2; Header 3=h3',
    branding: true,
    default_link_target: '_blank',
    table_grid: false,
    menubar: false,
    toolbar:
        'undo redo | styleselect | bold italic underline strikethrough backcolor | outdent indent | numlist bullist | link image | align | ltr rtl | table | removeformat | searchreplace | fullscreen',
    toolbar_groups: {
        align: {
            icon: 'aligncenter',
            tooltip: 'Align',
            items: 'alignleft aligncenter alignright alignjustify',
        },
    },
    table_toolbar:
        'tableprops tabledelete | tableinsertrowbefore tableinsertrowafter tabledeleterow | tableinsertcolbefore tableinsertcolafter tabledeletecol',

    style_formats: [
        {title: 'Heading 1', format: 'h1'},
        {title: 'Heading 2', format: 'h2'},
        {title: 'Heading 3', format: 'h3'},
        {title: 'Paragraph', format: 'p'},
    ],
    cleanup: true,
};

// adjust rich text editor theme based on mode
if (__settings__.dark) {
    tinyConfig.skin = 'oxide-dark';
    tinyConfig.content_css = 'dark';
}

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
    const pairs = this.map((x) => {
        return `${varName}=${x}`;
    });
    return pairs.join('&');
};

String.prototype.getFilename = function () {
    return this.substring(this.lastIndexOf('/') + 1)
        .replace(/[\#\?].*$/, '')
        .replace(/\.[^/.]+$/, '');
};
String.prototype.trunc = function (n) {
    return this.substr(0, n - 1) + (this.length > n ? '&hellip;' : '');
};

String.prototype.getInitials = function () {
    return this.split(' ')
        .map((word) => word[0].toUpperCase())
        .join('');
};

//helper method to translate front-end strings using an array of translation objects (constructed in i18n.jinja2)
function translate_status(str) {
    // placeholder, will handle translations in a future release
    return str;
}

String.prototype.toHHMMSS = function () {
    var sec_num = parseInt(this, 10); // don't forget the second param
    var hours = Math.floor(sec_num / 3600);
    var minutes = Math.floor((sec_num - hours * 3600) / 60);
    var seconds = sec_num - hours * 3600 - minutes * 60;

    if (hours < 10) {
        hours = '0' + hours;
    }
    if (minutes < 10) {
        minutes = '0' + minutes;
    }
    if (seconds < 10) {
        seconds = '0' + seconds;
    }
    return hours + ':' + minutes + ':' + seconds;
};

String.prototype.formatName = function () {
    let firstlast = this.split(' ');
    return firstlast[0].substr(0, 1).toUpperCase() + '.' + firstlast[1];
};

// relationship information helper

const extractValuesById = function(dataList, idList, valueKey)
{
    if (!idList || !dataList ) { // better check for null or undefined ..
        return [];
    }
    if (!Array.isArray(idList)) {
        idList = [idList];
    }

    return dataList.filter((item) => idList.includes(item.id)).map((item) => item[valueKey]);
}


// global helper methods for geolocations

const aggregateBulletinLocations = function (bulletin) {
    let locations = [];

    // Use map to create a new array with modifications
    let locs =
        bulletin.locations?.map((loc) => {
            return {...loc, color: '#00a1f1', parentId: bulletin.id};
        }) || [];

    locations = locations.concat(locs);

    // Handle geoLocations
    let geoLocations =
        bulletin.geoLocations?.map((loc, i) => {
            return {
                ...loc,
                number: i + 1,
                color: '#ffbb00',
                parentId: bulletin.id,
                type: loc.type?.title,
            };
        }) || [];

    locations = locations.concat(geoLocations);

    // event locations
    if (bulletin.events?.length) {
        const eventLocations = prepareEventLocations(bulletin.id, bulletin.events);
        locations = locations.concat(eventLocations);
    }
    return locations;
};

const aggregateActorLocations = function (actor) {
    let locations = [];

    const addLocation = (place, type) => {
        if (place && place.latlng) {
            locations.push({
                ...place,
                type: type,
                color: '#00a1f1',
                parentId: actor.id,
                lat: place.latlng.lat,
                lng: place.latlng.lng,
            });
        }
    };

    addLocation(actor.origin_place, 'Origin Place');

    // Event locations
    if (actor.events?.length) {


        const eventLocations = prepareEventLocations(actor.id, actor.events);

        locations = locations.concat(eventLocations);
    }
    

    return locations;
};

function prepareEventLocations(parentId, events) {
    let output = events.filter((x) => x.location && x.location.latlng);

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
        return x.location;
    });
}

function parseResponse(dzFile) {
    // helper method to convert xml response to friendly json format
    const response = JSON.parse(dzFile.xhr.response);

    return {
        uuid: dzFile.upload.uuid,
        type: dzFile.type,
        name: dzFile.name,
        s3url: response.filename,
        filename: response.filename,
        etag: response.etag,
    };
}

function getBulletinLocations(ids) {
    promises = [];
    ids.forEach((x) => {
        promises.push(
            axios.get(`/admin/api/bulletin/${x}?mode=3`).then((response) => {
                return aggregateBulletinLocations(response.data);
            }),
        );
    });
    return Promise.all(promises);
}

var aggregateIncidentLocations = function (incident) {
    let locations = [];

    if (incident.locations && incident.locations.length) {
        let locs = incident.locations.filter((x) => x.lat && x.lng);
        locs.map((x) => {
            x.color = '#00a1f1';
            return x;
        });
        locations = locations.concat(locs);
    }

    // event locations
    if (incident.events && incident.events.length) {
        let eventLocations = incident.events
            .filter((x) => x.location && x.location.lat && x.location.lng)
            .map((x, i) => {
                // exclude locations with null coordinates

                //attach serial number to events for map reference
                x.location.number = i + 1;
                x.location.title = x.title;
                x.location.color = '#00f166';
                return x.location;
            });

        locations = locations.concat(eventLocations);
    }
    return locations;
};

// videojs config settings  - prevent plugin from sending data
window.HELP_IMPROVE_VIDEOJS = false;

// media screenshots helper method
dataUriToBlob = function (dataURI) {
    // convert base64/URLEncoded data component to raw binary data held in a string
    var byteString;
    if (dataURI.split(',')[0].indexOf('base64') >= 0) byteString = atob(dataURI.split(',')[1]);
    else byteString = unescape(dataURI.split(',')[1]);

    // separate out the mime component
    var mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];

    // write the bytes of the string to a typed array
    var ia = new Uint8Array(byteString.length);
    for (var i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }

    return new Blob([ia], {type: mimeString});
};

// Media players
const DEFAULT_VIDEOJS_OPTIONS = {
    controls: true,
    preload: 'auto',
    playbackRates: VIDEO_RATES,
    fluid: true,
}
function buildVideoElement() {
    const videoElement = document.createElement('video');
    videoElement.className = 'video-js vjs-default-skin vjs-big-play-centered w-100';
    videoElement.setAttribute('crossorigin', 'anonymous');
    videoElement.setAttribute('controls', '');
    videoElement.setAttribute('width', '620');
    videoElement.setAttribute('height', '348');

    return videoElement;
}
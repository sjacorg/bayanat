// Common validation rules
// Each rule returns `true` if valid, or a string error message if invalid
let checkUsernameTimeout;
let passwordCheckTimeout;

const validationRules = {
    required: (message = window.translations.thisFieldIsRequired_) => {
        return v => hasValue(v) || message;
    },
    atLeastOneRequired: (value, message = window.translations.thisFieldIsRequired_) => {
        return v => hasValue(value) || message;
    },
    maxLength: (max, message) => {
        const defaultMessage = window.translations.mustBeMaxCharactersOrFewer_(max);
        return v => isValidLength(v, max, "max") || message || defaultMessage;
    },
    date(message = window.translations.invalidDate_) {
        return v => {
            if (!v) return true; // allow empty values
            return dayjs(v).isValid() || message;
        };
    },
    urlOrNA(message = window.translations.mustBeAValidUrlOrNa_) {
        return v => {
            if (!v) return true; // allow empty if not required
            if (v === 'NA') return true;
            try {
                new URL(v);
                return true;
            } catch {
                return message;
            }
        };
    },
    dateBeforeOtherDate(otherDate, message = window.translations.fromDateMustBeBeforeTheToDate_) {
        return v => {
            if (!v || !otherDate) return true;
            return dayjs(v).isSameOrBefore(dayjs(otherDate)) || message;
        };
    },
    dateAfterOtherDate(otherDate, message = window.translations.toDateMustBeAfterTheFromDate_) {
        return v => {
            if (!v || !otherDate) return true;
            return dayjs(v).isSameOrAfter(dayjs(otherDate)) || message;
        };
    },
    minLength: (min, message) => {
        const defaultMessage = window.translations.mustBeAtLeastCharacters_(min);
        return v => isValidLength(v, min, "min") || message || defaultMessage;
    },
    integer: (message) => {
        const defaultMessage = window.translations.pleaseEnterAValidNumber_;
        return v => !v || /^\d+$/.test(v) || message || defaultMessage;
    },
    checkUsername: ({ initialUsername, onResponse }) => {
        const defaultMsg = window.translations.usernameInvalidOrAlreadyTaken_;
      
        return v => new Promise(resolve => {
          clearTimeout(checkUsernameTimeout);
          checkUsernameTimeout = setTimeout(async () => {
            try {
              if (v === initialUsername) return onResponse(true), resolve(true);
      
              await axios.post('/admin/api/checkuser/', { item: v }, { suppressGlobalErrorHandler: true });
              onResponse(true);
              resolve(true);
            } catch (err) {
              onResponse(false);
              const status = err?.response?.status;
              resolve(
                status === 409 ? window.translations.usernameAlreadyTaken_ :
                status === 400 ? window.translations.usernameInvalid_ :
                defaultMsg
              );
            }
          }, 350);
        });
    },    
    matchesField: (otherValue, message) => {
        const defaultMessage = window.translations.fieldsDoNotMatch_;
        return v => v === otherValue || message || defaultMessage;
    },
    checkPassword: ({ onResponse }) => {
        const defaultMessage = window.translations.passwordTooWeak_;
        
      
        return (v) => {
          return new Promise((resolve) => {
            clearTimeout(passwordCheckTimeout);
      
            passwordCheckTimeout = setTimeout(async () => {
              try {
                await axios.post('/admin/api/password/', { password: v }, { suppressGlobalErrorHandler: true });
                onResponse(true);
                resolve(true);
            } catch (err) {
                onResponse(false);
                resolve(defaultMessage);
              }
            }, 350);
          });
        };
    },
    hexColor() {
        return (value) => {
            if (!value) return true; // Optional field
            const hexPattern = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$/;
            return hexPattern.test(value) || 'Invalid hex color format (e.g., #F53, #FF5733, or #FF5733FF)';
        };
    }
};

// Helper functions
function hasValue(value) {
  if (Array.isArray(value)) {
    return value.length > 0;
  }

  return value !== null && value !== undefined && value !== '';
}

function isValidLength(value, limit, type) {
    if (!value) return true; // Allow empty values
    const length = Array.isArray(value) ? value.length : value.length;
    return type === "max" ? length <= limit : length >= limit;
}

function scrollToFirstError() {
  const wrapper = document.querySelector(".v-input--error");
  if (!wrapper) return;

  wrapper.scrollIntoView({ behavior: 'smooth', block: 'center' });

  const input = wrapper.querySelector("input, textarea, select");
  if (input) setTimeout(() => input.focus(), 300);
}


// global vuetify config object passed to most pages of the system
const variables = {
    // Border radius
    'rounded-10': '10px',
    'rounded-12': '12px',
    'rounded-16': '16px',

    // Overflow
    'overflow-unset': 'unset',

    // Z-index
    'z-1': '1',
    'z-100': '100',

    // Position
    'left-auto': 'auto',

    // Height
    'h-fit': 'fit-content',

    // Pointer events
    'pointer-events-none': 'none',
    'pointer-events-auto': 'auto',
}
const vuetifyConfig = {
    defaults: {
        VRow: {
            dense: true,
        },
        VApp: {
            class: 'bg-background',
        },
        VColorInput: {
            variant: 'outlined',
        },
        VTextField: {
            variant: 'outlined',
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
        VAutocomplete: {
            variant: 'outlined'
        },
        VNumberInput: {
            variant: 'outlined'
        },
        VBtn: {
            rounded: 'lg',
            class: 'text-none font-weight-regular text-body-2 elevation-0',
        },
        VTab: {
            VBtn: {
                class: '', // Remove the custom classes from tab buttons
                rounded: 'none', // Reset the border radius
            },
        },
        VBtnGroup: {
            VBtn: {
                class: '', // Remove the custom classes from tab buttons
                rounded: 'none', // Reset the border radius
            },
        },
        VChip: {
            size: 'small'
        },
        VSwitch: {
            color: 'primary',
            density: 'compact'
        },
        VCheckbox: {
            density: 'compact'
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
                    'dark-primary': '#35857c',
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
                    background: '#FAFAFA',
                    muted: '#79747E',
                    border: '#D9D9D9',
                    'table-header': '#9E9E9E',
                    'table-body': '#666666',
                    'core-field-accent': '#ebebf0'
                },
                variables
            },
            dark: {
                dark: true, // Explicitly set the dark theme as dark
                colors: {
                    // Adapted to the more complex structure of your dark theme
                    primary: '#09a7a6',
                    'dark-primary': '#0a8786',
                    grey: '#999', // Only one shade represented for simplicity
                    'blue-grey': '#222', // Base color, assuming primary shade
                    gv: '#019985', // Darken2 shade assumed for simplicity
                    lime: '#303030',
                    teal: '#008080',
                    // You might need to adjust or add additional custom colors here
                    muted: '#A59E99',
                    border: '#444444',
                    'table-header': '#B0B0B0',
                    'table-body': '#ffffffb3'
                },
                variables
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

// Set axios defaults
axios.defaults.headers.common['Accept'] = 'application/json';

// Centralized API service - handles standardized responses transparently
const api = {
    get: axios.get.bind(axios),
    post: axios.post.bind(axios), 
    put: axios.put.bind(axios),
    delete: axios.delete.bind(axios)
};

//global axios response interceptor - handles standardized API responses and global error handling  
axios.interceptors.response.use(
    function (response) {
        const shouldFlatten =
            isPlainObject(response?.data?.data) &&
            !response?.config?.skipFlattening;
    
        if (shouldFlatten) {
            return {
                ...response,
                data: {
                    ...response.data.data,
                    ...(response.data?.message ? { message: response.data.message } : {})
                }
            };
        }
    
      return response;
    },
    function (error) {
        if (!error.config?.suppressGlobalErrorHandler) {
            const globalRequestErrorEvent = new CustomEvent('global-axios-error', { detail: error });
            document.dispatchEvent(globalRequestErrorEvent);
        }
        // Check for session expiration errors (401 Unauthorized)
        if ([401].includes(error?.response?.status)) {
            const authenticationRequiredEvent = new CustomEvent('authentication-required', { detail: error });
            document.dispatchEvent(authenticationRequiredEvent);
        }
        return Promise.reject(error);
    },
);

function isPlainObject(val) {
    return val !== null && typeof val === 'object' && !Array.isArray(val);
}

function isEmptyObject(obj) {
  return !obj || Object.keys(obj).length === 0;
}

function getInfraMessage(status) {
    switch (status) {
        case 502:
        case 503:
            return 'The service is currently unavailable. Please try again in a few moments.';
        case 500:
            return 'A server error occurred. Please try again or reach out to support.';
        default:
            return 'An unexpected error occurred. If this continues, please contact support.';
    }
}
  
 function handleRequestError(error) {
    const response = error?.response;
  
    // Handle known API error format
    if (response?.data?.response?.errors) {
      return response.data.response.errors.join('\n');
    }
  
    if (response?.data?.errors) {
      const errors = response.data.errors;
      return Object.entries(errors).map(([field, message]) => {
        const fieldName = field.startsWith('item.') ? field.slice(5) : field;
        const label = fieldName.includes('__root__') ? 'Validation Error' : fieldName;
        return `<span class="font-weight-bold text-red">[${label}]</span>: ${message}`;
      }).join('<br />') || 'An error occurred.';
    }

    if (response?.data?.message) {
        return response.data.message;
    }

     // Check for HTML response by Content-Type header
     const ct = response?.headers?.['content-type'] || '';
     if (ct.includes('text/html') && response?.status) {
         return getInfraMessage(response.status);
     }

     // Fallback: detect HTML content via DOMParser
     if (typeof response?.data === 'string') {
         try {
             const doc = new DOMParser().parseFromString(response.data, 'text/html');
             if (doc.body.children.length && response?.status) {
                 return getInfraMessage(response.status);
             }
             return response.data; // It's a plain string, safe to show
         } catch {
             return 'Unexpected error occurred while processing server response.';
         }
     }
  
    // No response from server (network issue, timeout, etc.)
    if (error.request) {
      return 'No response from server. Contact an admin.';
    }
  
    // Axios or JS-level error
    if (error?.message) {
      return error.message || 'An error occurred.';
    }
  
    // Total fallback
    return 'Request failed. Check your network connection.';
}

//  in-page router for bulletins/actors/incidents pages
const {createRouter, createWebHistory, createWebHashHistory} = VueRouter;

const routes = [
    {path: '/', name: 'home', component: Vue.defineComponent({template: ''})},

    {path: '/admin/bulletins/:id', name: 'bulletin', component: Vue.defineComponent({})},
    {path: '/admin/bulletins/', name: 'bulletins', component: Vue.defineComponent({})},
    {path: '/admin/bulletin-fields/', name: 'bulletin-fields', component: Vue.defineComponent({})},
    {path: '/admin/actors/:id', name: 'actor', component: Vue.defineComponent({})},
    {path: '/admin/actors/', name: 'actors', component: Vue.defineComponent({})},
    {path: '/admin/actor-fields/', name: 'actor-fields', component: Vue.defineComponent({})},
    {path: '/admin/incidents/:id', name: 'incident', component: Vue.defineComponent({})},
    {path: '/admin/incidents/', name: 'incidents', component: Vue.defineComponent({})},
    {path: '/admin/incident-fields/', name: 'incident-fields', component: Vue.defineComponent({})},
    {path: '/admin/locations/:id', name: 'location', component: Vue.defineComponent({})},
    {path: '/admin/locations/', name: 'locations', component: Vue.defineComponent({})},
    {path: '/admin/activity/', name: 'activity', component: Vue.defineComponent({})},
    {path: '/export/dashboard/:id', name: 'export', component: Vue.defineComponent({})},
    {path: '/export/dashboard/', name: 'exports', component: Vue.defineComponent({})},
    {path: '/import/log/:id', name: 'log', component: Vue.defineComponent({})},
    {path: '/import/log/', name: 'logs', component: Vue.defineComponent({})},
    {path: '/admin/users/:id', name: 'user', component: Vue.defineComponent({})},
    {path: '/admin/users/', name: 'users', component: Vue.defineComponent({})},
    { path: '/admin/component-data/', name: 'component-data', component: Vue.defineComponent({}) },
    { path: '/admin/system-administration/', name: 'system-administration', component: Vue.defineComponent({}) },

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
        'undo redo | styleselect | bold italic underline strikethrough backcolor | outdent indent | numlist bullist | link image | alignleft aligncenter alignright alignjustify | ltr rtl | table | removeformat | searchreplace | fullscreen',

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
String.prototype.getFilename = function () {
    return this.substring(this.lastIndexOf('/') + 1)
        .replace(/[\#\?].*$/, '')
        .replace(/\.[^/.]+$/, '');
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
            return { ...loc, color: '#00a1f1', parentId: bulletin.id, class_type: 'bulletin' };
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
                class_type: 'bulletin',
                type: loc.type?.title,
            };
        }) || [];

    locations = locations.concat(geoLocations);

    // event locations
    if (bulletin.events?.length) {
        const eventLocations = prepareEventLocations(bulletin.id, bulletin.events, 'bulletin');
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
                class_type: 'actor',
                lat: place.latlng.lat,
                lng: place.latlng.lng,
            });
        }
    };

    addLocation(actor.origin_place, 'Origin Place');

    // Event locations
    if (actor.events?.length) {


        const eventLocations = prepareEventLocations(actor.id, actor.events, 'actor');

        locations = locations.concat(eventLocations);
    }
    

    return locations;
};

function prepareEventLocations(parentId, events, class_type) {
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
        x.location.class_type = class_type;
        x.location.color = '#00f166';
        x.location.lat = x.location.latlng.lat;
        x.location.lng = x.location.latlng.lng;
        x.location.zombie = x.from_date === null && x.to_date === null;
        x.location.from_date = x.from_date ?? null;
        x.location.to_date = x.to_date ?? null;
        x.location.estimated = Boolean(x.estimated);
        x.location.eventtype = x.eventtype?.title;
        return x.location;
    });
}

function findUploadedFileByUUID(acceptedFiles, uuid) {
    const file = acceptedFiles.find(
        file => file.status === 'success' && normalizeDropzoneResponse(file).uuid === uuid
    );

    if (!file) {
        console.warn('Could not find matching file for UUID:', uuid);
        return null;
    }

    return normalizeDropzoneResponse(file);
}

function normalizeDropzoneResponse(dzFile) {
    // helper method to convert xml response to friendly json format
    const response = JSON.parse(dzFile.xhr.response);

    return {
        uuid: dzFile.upload.uuid,
        type: dzFile.type,
        name: dzFile.name,
        s3url: response.data.filename,
        filename: response.data.filename,
        etag: response.data.etag,
        original_filename: response.data.original_filename,
    };
}

function getBulletinLocations(ids) {
    return Promise.all(
        ids.map(id =>
            api.get(`/admin/api/bulletin/${id}?mode=3`).then(res =>
                aggregateBulletinLocations(res.data)
            )
        )
    );
}

function getActorLocations(ids) {
    return Promise.all(
        ids.map(id =>
            api.get(`/admin/api/actor/${id}?mode=3`).then(res =>
                aggregateActorLocations(res.data)
            )
        )
    );
}

var aggregateIncidentLocations = function (incident) {
    let locations = [];

    if (incident.locations && incident.locations.length) {
        let locs = incident.locations.filter((x) => x.lat && x.lng);
        locs.map((x) => {
            x.color = '#00a1f1';
            x.class_type = 'incident';
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
                x.location.class_type = 'incident';
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
    videoElement.className = 'video-js vjs-default-skin vjs-big-play-centered vjs-16-9 h-100 pa-0';
    videoElement.setAttribute('crossorigin', 'anonymous');
    videoElement.setAttribute('controls', '');
    videoElement.setAttribute('width', '620');
    videoElement.setAttribute('height', '348');

    return videoElement;
}

// Deep clone utility for nested refs or reactive data
function deepClone(value) {
    try {
        return structuredClone(value);
    } catch (error) {
        return JSON.parse(JSON.stringify(value));
    }
}

// Load external script dynamically with caching
const loadedScripts = new Map();
function loadScript(src) {
  if (loadedScripts.has(src)) {
    return loadedScripts.get(src);
  }

  const isModule = src.endsWith('.mjs');
  
  const promise = (async () => {
    // For ES modules, use dynamic import
    if (isModule) {
      return await import(src);
    }
    
    // For regular scripts, use the existing logic
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Failed to load script: ${src}`));

      document.head.appendChild(script);
    });
  })();

  loadedScripts.set(src, promise);
  return promise;
}
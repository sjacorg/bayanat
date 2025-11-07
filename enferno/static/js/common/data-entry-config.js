const vuetifyConfig = {
    defaults: {
        VRow: {
            dense: true,
        },
        VApp: {
            class: 'bg-background',
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
        VBtn: {
            rounded: 'lg',
            class: 'text-none font-weight-regular text-body-2',
            elevation: '0',
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
                    'table-body': '#666666'
                },
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
            },
        },
    },
    // Preserve other configurations outside the theme structure
    icons: {
        iconfont: 'mdi',
    },
};

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
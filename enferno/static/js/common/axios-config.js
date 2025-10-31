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
const globalMixin = {

    methods: {

        // Snack Bar
        showSnack(message) {
            this.snackMessage = message;
            this.snackbar = true;
        },

        has_role(user, role) {
            for (const r of user.roles) {
                if (r.name === role) {
                    return true
                }
            }
            return false;
        }

    }

}
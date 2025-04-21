const DiffTool = {
    hasDiff: function (obj1 = {}, obj2 = {}) {
        return Object.keys(DiffTool.getDiff(obj1, obj2)).length;
    },

    getDiff: function (obj1 = {}, obj2 = {}) {
        const diff = {};

        const diffRecursive = (a, b, currentPath) => {
            if (Array.isArray(a) && Array.isArray(b)) {
                // If arrays are different, include the whole array in the diff
                if (JSON.stringify(a) !== JSON.stringify(b)) {
                    diff[currentPath] = { old: a, new: b };
                }
            } else if (typeof a === 'object' && typeof b === 'object' && a !== null && b !== null) {
                // Compare objects key by key
                const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
                for (const key of keys) {
                    const newPath = currentPath ? `${currentPath}.${key}` : key;
                    diffRecursive(a[key], b[key], newPath);
                }
            } else if (a !== b) {
                // If primitive values differ, add to diff
                diff[currentPath] = { old: a, new: b };
            }
        };

        // Top-level comparison to group changes by entire objects if needed
        if (typeof obj1 === 'object' && typeof obj2 === 'object') {
            const keys = new Set([...Object.keys(obj1 ?? {}), ...Object.keys(obj2 ?? {})]);
            for (const key of keys) {
                const oldValue = obj1[key];
                const newValue = obj2[key];

                if (Array.isArray(oldValue) && Array.isArray(newValue)) {
                    // Compare arrays as a whole
                    if (JSON.stringify(oldValue) !== JSON.stringify(newValue)) {
                        diff[key] = { old: oldValue, new: newValue };
                    }
                } else if (typeof oldValue === 'object' && typeof newValue === 'object') {
                    const nestedDiff = this.getDiff(oldValue, newValue);
                    if (Object.keys(nestedDiff).length > 0) {
                        diff[key] = { old: oldValue, new: newValue };
                    }
                } else if (oldValue !== newValue) {
                    diff[key] = { old: oldValue, new: newValue };
                }
            }
        }

        return diff;
    },

    renderDiff: function (diff, translations = {}) {
        const formatValue = (value) => {
            if (value === undefined || value === null || value === "") return '<span style="font-style: italic;">UNSET</span>';
            if (Array.isArray(value)) {
                return `${value.map(formatValue).join(', ')}`;
            }
            if (typeof value === 'object') {
                return `<ul>${Object.entries(value)
                    .map(([key, val]) => `<li><strong>${key}</strong>: ${formatValue(val)}</li>`)
                    .join('')}</ul>`;
            }
            if (typeof value === 'string') return `${value}`;
            if (typeof value === 'boolean') return value ? 'On' : 'Off';
            return value;
        };

        const translateKey = (key) => translations[key] || key;

        const diffHtml = Object.entries(diff).map(([key, change]) => {
            const translatedKey = translateKey(key);
            if (change.old === undefined) {
                return `<li><strong>${translatedKey}</strong>: <span style="color: green;">${formatValue(change.new)}</span></li>`;
            } else if (change.new === undefined) {
                return `<li><strong>${translatedKey}</strong>: <span style="color: red;">${formatValue(change.old)}</span></li>`;
            } else {
                return `<li><strong>${translatedKey}</strong>: <span style="color: red;">${formatValue(change.old)}</span> → <span style="color: green;">${formatValue(change.new)}</span></li>`;
            }
        });

        return `<ul>${diffHtml.join('')}</ul>`;
    },

    getAndRenderDiff(obj1 = {}, obj2 = {}, translations = {}) {
        const diff = DiffTool.getDiff(obj1, obj2);
        return DiffTool.renderDiff(diff, translations);
    }
};
const DiffTool = {
    hasDiff: function (obj1 = {}, obj2 = {}) {
        return Object.keys(DiffTool.getDiff(obj1, obj2)).length;
    },

    getDiff: function (obj1 = {}, obj2 = {}) {
        const diff = {};

        const diffRecursive = (a, b, currentPath) => {
            if (Array.isArray(a) && Array.isArray(b)) {
                if (JSON.stringify(a) !== JSON.stringify(b)) {
                    diff[currentPath] = { old: a, new: b };
                }
            } else if (typeof a === 'object' && typeof b === 'object' && a !== null && b !== null) {
                const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
                for (const key of keys) {
                    const newPath = currentPath ? `${currentPath}.${key}` : key;
                    diffRecursive(a[key], b[key], newPath);
                }
            } else if (a !== b) {
                diff[currentPath] = { old: a, new: b };
            }
        };

        diffRecursive(obj1, obj2, '');
        return diff;
    },

    renderDiff: function (diff, translations = {}) {
        const formatValue = (value) => {
            if (value === undefined || value === null || value === "") return '<span class="font-italic">UNSET</span>';
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

        const translateKey = (key) => {
            const parts = key.split('.');
            if (parts.length > 1) {
                const [top, ...rest] = parts;
                const topLabel = translations[top] || top;
                const subPath = rest.join('.');
                return `${topLabel} <b>(${subPath.toUpperCase()})</b>`;
            }
            return translations[key] || key;
        };

        const entries = Object.entries(diff);

        const diffHtml = entries.map(([key, change], index) => {
            const translatedKey = translateKey(key);
            const isLast = index === entries.length - 1;
            const borderClass = isLast ? '' : 'border-b';
            const cellClass = `${borderClass} pb-1 pt-1`;

            if (change.old === undefined) {
                return `<tr>
                            <td class="${cellClass}">${translatedKey}</td>
                            <td class="${cellClass}"></td>
                            <td class="${cellClass} text-green-lighten-1">${formatValue(change.new)}</td>
                        </tr>`;
            } else if (change.new === undefined) {
                return `<tr>
                            <td class="${cellClass}">${translatedKey}</td>
                            <td class="${cellClass} text-red-lighten-1">${formatValue(change.old)}</td>
                            <td class="${cellClass}"></td>
                        </tr>`;
            } else {
                return `<tr>
                            <td class="${cellClass}">${translatedKey}</td>
                            <td class="${cellClass} text-red-lighten-1">${formatValue(change.old)}</td>
                            <td class="${cellClass} text-green-lighten-1">${formatValue(change.new)}</td>
                        </tr>`;
            }
        });


        return `<table class="text-left w-100" style="table-layout: fixed;">
                    <thead>
                        <th class="border-b pb-1 pt-1">Setting</th>
                        <th class="border-b pb-1 pt-1">Before</th>
                        <th class="border-b pb-1 pt-1">After</th>
                    </thead>
                    <tbody>
                        ${diffHtml.join('')}
                    </tbody>
                </table>`;
        // const diffHtml = Object.entries(diff).map(([key, change]) => {
        //     const translatedKey = translateKey(key);
        //     if (change.old === undefined) {
        //         return `<li><strong>${translatedKey}</strong>: <span class="text-green-lighten-1">${formatValue(change.new)}</span></li>`;
        //     } else if (change.new === undefined) {
        //         return `<li><strong>${translatedKey}</strong>: <span class="text-red-lighten-1">${formatValue(change.old)}</span></li>`;
        //     } else {
        //         return `<li><strong>${translatedKey}</strong>: <span class="text-red-lighten-1">${formatValue(change.old)}</span> → <span class="text-green-lighten-1">${formatValue(change.new)}</span></li>`;
        //     }
        // });

        // return `<ul>${diffHtml.join('')}</ul>`;
    },

    getAndRenderDiff(obj1 = {}, obj2 = {}, translations = {}) {
        const diff = DiffTool.getDiff(obj1, obj2);
        console.log({obj1, obj2, diff})
        return DiffTool.renderDiff(diff, translations);
    }
};
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

    renderDiff: function (diff, labels = {}) {
        const formatValue = (value, options) => {
            if (value === undefined || value === null || value === "") return `<span class="font-italic">${window?.translations?.unset_ ?? 'UNSET'}</span>`;
            if (Array.isArray(value)) {
                return `${value.map(formatValue).join(', ')}`;
            }
            if (typeof value === 'object') {
                const childEntries = Object.entries(value)
                
                return `<ul>${childEntries
                    .map(([key, val], index) => {
                        const isLast = index === childEntries.length - 1
                        const indentClass = options?.hasParent ? 'ml-2' : '';
                        const marginClass = options?.hasParent || isLast ? '' : 'mb-2';

                        return `<li class="${[indentClass, marginClass].filter(Boolean).join(' ')}">${key.toUpperCase()}: ${formatValue(val, { hasParent: true })}</li>`
                    })
                    .join('')}</ul>`;
            }
            if (typeof value === 'string') return `${value}`;
            if (typeof value === 'boolean') return value ? `${window?.translations?.on_ ?? 'On'}` : `${window?.translations?.off_ ?? 'Off'}`;
            return value;
        };

        const toTitleCase = (str) => {
            return str
                .replace(/_/g, ' ') // replace underscores with spaces
                .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase());
        };

        const translateKey = (key) => {
            const customLabels = {
                IN_APP_ENABLED: window.translations.inApp_,
                EMAIL_ENABLED: window.translations.email_,
                GOOGLE_OAUTH_ENABLED: window.translations.googleOauth_,
            }

            const parts = key.toUpperCase().split('.');
            if (parts.length > 1) {
                const nextKey = key.toUpperCase().replaceAll('.', '_')
                if (labels[nextKey]) {
                    return customLabels?.[key] || labels[nextKey]
                } else {
                    const [top, ...rest] = parts;
                    const topLabel = customLabels?.[top] || labels[top] || top;
                    const subPath = rest.map(pathKey => customLabels?.[pathKey] || toTitleCase(pathKey)).join(' → ');
                    return `${topLabel} <b>(${subPath})</b>`;
                }

            }
            return customLabels?.[key] || labels[key] || toTitleCase(key);
        };

        const diffEntries = Object.entries(diff);

        const diffHtml = diffEntries.map(([key, change], index) => {
            const translatedKey = translateKey(key);
            const isLast = index === diffEntries.length - 1;
            const borderClass = isLast ? '' : 'border-b';
            const cellClass = `${borderClass} pa-1`;
            const cellStyle = `vertical-align: top;`;

            if (change.old === undefined) {
                return `<tr>
                            <td style="${cellStyle}" class="${cellClass} text-caption">${translatedKey}</td>
                            <td style="${cellStyle}" class="${cellClass}"></td>
                            <td style="${cellStyle}" class="${cellClass} text-green-lighten-1">${formatValue(change.new)}</td>
                        </tr>`;
            } else if (change.new === undefined) {
                return `<tr>
                            <td style="${cellStyle}" class="${cellClass} text-caption">${translatedKey}</td>
                            <td style="${cellStyle}" class="${cellClass} text-red-lighten-1">${formatValue(change.old)}</td>
                            <td style="${cellStyle}" class="${cellClass}"></td>
                        </tr>`;
            } else {
                return `<tr>
                            <td style="${cellStyle}" class="${cellClass} text-caption">${translatedKey}</td>
                            <td style="${cellStyle}" class="${cellClass} text-red-lighten-1">${formatValue(change.old)}</td>
                            <td style="${cellStyle}" class="${cellClass} text-green-lighten-1">${formatValue(change.new)}</td>
                        </tr>`;
            }
        });

        return `<table class="text-left w-100" style="table-layout: fixed; border-collapse: collapse;">
                    <thead>
                        <th class="border-b pa-1">${window?.translations?.setting_ ?? 'Setting'}</th>
                        <th class="border-b pa-1">${window?.translations?.before_ ?? 'Before'}</th>
                        <th class="border-b pa-1">${window?.translations?.after_ ?? 'After'}</th>
                    </thead>
                    <tbody>
                        ${diffHtml.join('')}
                    </tbody>
                </table>`;
    },

    getAndRenderDiff(obj1 = {}, obj2 = {}, labels = {}) {
        const diff = DiffTool.getDiff(obj1, obj2);
        return DiffTool.renderDiff(diff, labels);
    }
};
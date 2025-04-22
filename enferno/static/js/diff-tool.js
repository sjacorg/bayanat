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
        const formatValue = (value) => {
            if (value === undefined || value === null || value === "") return `<span class="font-italic">${window?.translations?.unset_ ?? 'UNSET'}</span>`;
            if (Array.isArray(value)) {
                return `${value.map(formatValue).join(', ')}`;
            }
            if (typeof value === 'object') {
                return `<div>${Object.entries(value)
                    .map(([key, val]) => `<div>${key}: ${formatValue(val)}</div>`)
                    .join('')}</div>`;
            }
            if (typeof value === 'string') return `${value}`;
            if (typeof value === 'boolean') return value ? `${window?.translations?.on_ ?? 'On'}` : `${window?.translations?.off_ ?? 'Off'}`;
            return value;
        };

        const translateKey = (key) => {
            const parts = key.toUpperCase().split('.');
            if (parts.length > 1) {
                const nextKey = key.toUpperCase().replaceAll('.', '_')
                if (labels[nextKey]) {
                    return labels[nextKey]
                } else {
                    const [top, ...rest] = parts;
                    const topLabel = labels[top] || top;
                    const subPath = rest.join('.');
                    return `${topLabel} <b>(${subPath})</b>`;
                }

            }
            return labels[key] || key;
        };

        const entries = Object.entries(diff);

        const diffHtml = entries.map(([key, change], index) => {
            const translatedKey = translateKey(key);
            const isLast = index === entries.length - 1;
            const borderClass = isLast ? '' : 'border-b';
            const cellClass = `${borderClass} pa-1`;

            if (change.old === undefined) {
                return `<tr>
                            <td class="${cellClass} text-caption">${translatedKey}</td>
                            <td class="${cellClass}"></td>
                            <td class="${cellClass} text-green-lighten-1">${formatValue(change.new)}</td>
                        </tr>`;
            } else if (change.new === undefined) {
                return `<tr>
                            <td class="${cellClass} text-caption">${translatedKey}</td>
                            <td class="${cellClass} text-red-lighten-1">${formatValue(change.old)}</td>
                            <td class="${cellClass}"></td>
                        </tr>`;
            } else {
                return `<tr>
                            <td class="${cellClass} text-caption">${translatedKey}</td>
                            <td class="${cellClass} text-red-lighten-1">${formatValue(change.old)}</td>
                            <td class="${cellClass} text-green-lighten-1">${formatValue(change.new)}</td>
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
const DiffTool = {
    hasDiff(obj1 = {}, obj2 = {}) {
        return Object.keys(DiffTool.getDiff(obj1, obj2)).length > 0;
    },

    getDiff(obj1 = {}, obj2 = {}, options = {}) {
        const diff = {};
        const idKey = options.idKey || "id";

        const diffRecursive = (a, b, currentPath) => {
            if (Array.isArray(a) && Array.isArray(b)) {
                // If objects with IDs → compare by ID
                if (a.every(x => typeof x === "object" && x?.[idKey]) &&
                    b.every(x => typeof x === "object" && x?.[idKey])) {
                    
                    const mapA = new Map(a.map(item => [item[idKey], item]));
                    const mapB = new Map(b.map(item => [item[idKey], item]));

                    // Detect removed
                    for (const [id, itemA] of mapA) {
                        if (!mapB.has(id)) {
                            diff[`${currentPath}[${id}]`] = { old: itemA, new: undefined };
                        }
                    }

                    // Detect added or changed
                    for (const [id, itemB] of mapB) {
                        if (!mapA.has(id)) {
                            diff[`${currentPath}[${id}]`] = { old: undefined, new: itemB };
                        } else {
                            diffRecursive(mapA.get(id), itemB, `${currentPath}[${id}]`);
                        }
                    }
                } else {
                    // Fallback: index-based comparison
                    const maxLen = Math.max(a.length, b.length);
                    for (let i = 0; i < maxLen; i++) {
                        const newPath = `${currentPath}[${i}]`;
                        diffRecursive(a[i], b[i], newPath);
                    }
                }
            } else if (
                typeof a === "object" &&
                typeof b === "object" &&
                a !== null &&
                b !== null
            ) {
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
                        const marginClass = options?.hasParent || isLast ? '' : 'mb-1';

                        return `<li class="${[indentClass, marginClass].filter(Boolean).join(' ')}">${key.toUpperCase()}: ${formatValue(val, { hasParent: true })}</li>`
                    })
                    .join('')}</ul>`;
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
                    const subPath = rest.join(' → ');
                    return `${topLabel} <b>(${subPath})</b>`;
                }

            }
            return labels[key] || key;
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
                        <th class="border-b pa-1">${window?.translations?.field_ ?? 'Field'}</th>
                        <th class="border-b pa-1">${window?.translations?.previous_ ?? 'Previous'}</th>
                        <th class="border-b pa-1">${window?.translations?.updated_ ?? 'Updated'}</th>
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
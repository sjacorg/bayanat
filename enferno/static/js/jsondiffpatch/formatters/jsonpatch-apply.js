import clone from "../clone.js";
/**
 * an implementation of JSON-Patch (RFC 6902) apply.
 *
 * this is atomic (if any errors occur, a rollback is performed before return)
 *
 * Note: this is used for testing to ensure the JSON-Patch formatter output is correct
 *
 * @param target an object to patch (this object will be modified, clone first if you want to avoid mutation)
 * @param patch a JSON-Patch procuded by jsondiffpatch jsonpatch formatter
 * (this is a subset of the whole spec, supporting only add, remove, replace and move operations)
 * @returns
 */
export const applyJsonPatchRFC6902 = (target, patch) => {
    const log = [];
    for (const op of patch) {
        try {
            switch (op.op) {
                case "add":
                    log.push({ result: add(target, op.path, op.value), op });
                    break;
                case "remove":
                    log.push({ result: remove(target, op.path), op });
                    break;
                case "replace":
                    log.push({ result: replace(target, op.path, op.value), op });
                    break;
                case "move":
                    log.push({ result: move(target, op.path, op.from), op });
                    break;
                case "copy":
                    log.push({ result: copy(target, op.path, op.from), op });
                    break;
                case "test":
                    log.push({ result: test(target, op.path, op.value), op });
                    break;
                default:
                    op;
                    throw new Error(`operation not recognized: ${JSON.stringify(op)}`);
            }
        }
        catch (error) {
            rollback(target, log, error instanceof Error ? error : new Error(String(error)));
            throw error;
        }
    }
};
const rollback = (target, log, patchError) => {
    try {
        for (const { op, result } of log.reverse()) {
            switch (op.op) {
                case "add":
                    unadd(target, op.path, result);
                    break;
                case "remove":
                    add(target, op.path, result);
                    break;
                case "replace":
                    replace(target, op.path, result);
                    break;
                case "move":
                    remove(target, op.path);
                    try {
                        add(target, op.from, result);
                    }
                    catch (error) {
                        // 2nd step failed, rollback 1st step
                        add(target, op.path, result);
                        throw error;
                    }
                    break;
                case "copy":
                    remove(target, op.path);
                    break;
                case "test":
                    // test op does not change the target
                    break;
                default:
                    op;
                    throw new Error(`operation not recognized: ${JSON.stringify(op)}`);
            }
        }
    }
    catch (error) {
        // this is unexpected, the rollback should not fail, target might be in an inconsistent state
        const message = (error instanceof Error ? error : new Error(String(error)))
            .message;
        throw new Error(`patch failed (${patchError.message}), and rollback failed too (${message}), target might be in an inconsistent state`);
    }
};
const UNSAFE_KEYS = new Set(["__proto__", "constructor", "prototype"]);
function parsePathFromRFC6902(path, { safe = true } = {}) {
    if (typeof path !== "string")
        return path;
    if (path.substring(0, 1) !== "/") {
        throw new Error("JSONPatch paths must start with '/'");
    }
    const parts = path
        .slice(1)
        .split("/")
        .map((part) => part.indexOf("~") === -1
        ? part
        : part.replace(/~1/g, "/").replace(/~0/g, "~"));
    for (const part of parts) {
        if (UNSAFE_KEYS.has(part)) {
            if (!safe)
                return null;
            throw new Error(`JSONPatch path segment "${part}" is not allowed (prototype pollution)`);
        }
    }
    return parts;
}
const get = (obj, path) => {
    const parts = Array.isArray(path) ? path : parsePathFromRFC6902(path);
    return parts.reduce((acc, key) => {
        if (Array.isArray(acc)) {
            const index = Number.parseInt(key, 10);
            if (index < 0 || index > acc.length - 1) {
                throw new Error(`cannot find /${parts.join("/")} in ${JSON.stringify(obj)} (index out of bounds)`);
            }
            return acc[index];
        }
        if (typeof acc !== "object" || acc === null || !(key in acc)) {
            throw new Error(`cannot find /${parts.join("/")} in ${JSON.stringify(obj)}`);
        }
        if (key in acc) {
            return acc[key];
        }
    }, obj);
};
const add = (obj, path, value) => {
    // see https://datatracker.ietf.org/doc/html/rfc6902#section-4.1
    // Silently skip operations on unsafe paths (prototype pollution prevention).
    const parts = parsePathFromRFC6902(path, { safe: false });
    if (parts === null)
        return;
    const last = parts.pop();
    const parent = get(obj, parts);
    if (Array.isArray(parent)) {
        const index = last === "-" ? parent.length : Number.parseInt(last, 10);
        if (Number.isNaN(index) || index < 0 || index > parent.length) {
            throw new Error(`cannot set /${parts.concat([last]).join("/")} in ${JSON.stringify(obj)} (index out of bounds)`);
        }
        // insert at index
        parent.splice(index, 0, clone(value));
        return;
    }
    if (last === "-") {
        throw new Error("JSONPatch 'add' with '-' requires array target");
    }
    if (typeof parent !== "object" || parent === null) {
        throw new Error(`cannot set /${parts.concat([last]).join("/")} in ${JSON.stringify(obj)}`);
    }
    /// set (or update) property
    const existing = parent[last];
    parent[last] = clone(value);
    return existing;
};
const remove = (obj, path) => {
    // see https://datatracker.ietf.org/doc/html/rfc6902#section-4.2
    const parts = parsePathFromRFC6902(path);
    const last = parts.pop();
    if (last === "-") {
        throw new Error("JSONPatch 'remove' path cannot end with '-'");
    }
    const parent = get(obj, parts);
    if (Array.isArray(parent)) {
        const index = Number.parseInt(last, 10);
        if (index < 0 || index > parent.length - 1) {
            throw new Error(`cannot delete /${parts.concat([last]).join("/")} from ${JSON.stringify(obj)} (index out of bounds)`);
        }
        // remove from index
        return parent.splice(index, 1)[0];
    }
    if (typeof parent !== "object" || parent === null) {
        throw new Error(`cannot delete /${parts.concat([last]).join("/")} from ${JSON.stringify(obj)}`);
    }
    // remove property
    const existing = parent[last];
    delete parent[last];
    return existing;
};
const unadd = (obj, path, previousValue) => {
    // used for rollbacks,
    // this is the reverse of add
    // (similar to remove, but it can also restore previous property value)
    const parts = parsePathFromRFC6902(path);
    const last = parts.pop();
    const parent = get(obj, parts);
    if (Array.isArray(parent)) {
        const index = last === "-" ? parent.length - 1 : Number.parseInt(last, 10);
        if (Number.isNaN(index) || index < 0 || index > parent.length - 1) {
            throw new Error(`cannot un-add (rollback) /${parts
                .concat([last])
                .join("/")} from ${JSON.stringify(obj)} (index out of bounds)`);
        }
        // remove from index
        parent.splice(index, 1);
    }
    if (typeof parent !== "object" || parent === null) {
        throw new Error(`cannot un-add (rollback) /${parts
            .concat([last])
            .join("/")} from ${JSON.stringify(obj)}`);
    }
    // remove property
    delete parent[last];
    if (previousValue !== undefined) {
        parent[last] = previousValue;
    }
};
const replace = (obj, path, value) => {
    // see https://datatracker.ietf.org/doc/html/rfc6902#section-4.3
    const parts = parsePathFromRFC6902(path);
    const last = parts.pop();
    if (last === "-") {
        throw new Error("JSONPatch 'replace' path cannot end with '-'");
    }
    const parent = get(obj, parts);
    if (Array.isArray(parent)) {
        const index = Number.parseInt(last, 10);
        if (index < 0 || index > parent.length - 1) {
            throw new Error(`cannot replace /${parts.concat([last]).join("/")} in ${JSON.stringify(obj)} (index out of bounds)`);
        }
        // replace at index
        const existing = parent[index];
        parent[index] = clone(value);
        return existing;
    }
    if (typeof parent !== "object" || parent === null) {
        throw new Error(`cannot replace /${parts.concat([last]).join("/")} in ${JSON.stringify(obj)}`);
    }
    /// replace property value
    const existing = parent[last];
    parent[last] = clone(value);
    return existing;
};
const move = (obj, path, from) => {
    // see https://datatracker.ietf.org/doc/html/rfc6902#section-4.4
    // '-' is only valid for add
    const pathLast = parsePathFromRFC6902(path).slice(-1)[0];
    if (pathLast === "-") {
        throw new Error("JSONPatch 'move' path cannot end with '-'");
    }
    const value = remove(obj, from);
    try {
        add(obj, path, value);
    }
    catch (error) {
        // 2nd step failed, rollback 1st step. keep this 2-step operation atomic
        add(obj, from, value);
        throw error;
    }
};
const copy = (obj, path, from) => {
    // see https://datatracker.ietf.org/doc/html/rfc6902#section-4.5
    // '-' is only valid for add
    const pathLast = parsePathFromRFC6902(path).slice(-1)[0];
    if (pathLast === "-") {
        throw new Error("JSONPatch 'copy' path cannot end with '-'");
    }
    const value = get(obj, from);
    return add(obj, path, clone(value));
};
const test = (obj, path, value) => {
    // see https://datatracker.ietf.org/doc/html/rfc6902#section-4.5
    const last = parsePathFromRFC6902(path).slice(-1)[0];
    if (last === "-") {
        throw new Error("JSONPatch 'test' path cannot end with '-'");
    }
    const actualValue = get(obj, path);
    if (JSON.stringify(value) !== JSON.stringify(actualValue)) {
        throw new Error(`test failed for /${path} in ${JSON.stringify(obj)} (expected: ${JSON.stringify(value)}, found: ${JSON.stringify(actualValue)})`);
    }
};

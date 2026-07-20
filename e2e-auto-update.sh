#!/usr/bin/env bash
#
# End-to-end test for the `bayanat update` pipeline on a disposable
# Hetzner VM. Provisions → installs → runs S1-S4 → teardown.
#
# Requires:
#   - hcloud CLI authenticated to the right project (see `hcloud context list`)
#   - ssh-agent loaded with the private key matching the registered hcloud key
#   - a public test fork with tags v4.0.0 (baseline), v4.0.1 (additive),
#     v4.0.2 (bad migration), v4.0.3 (/health 503 at runtime), v4.0.4 (recovery)
#
# Usage:
#   ./e2e-auto-update.sh                    # full run: provision → S1-S4 → destroy
#   KEEP_VM=1 ./e2e-auto-update.sh          # leave VM running at end
#   VM_IP=1.2.3.4 ./e2e-auto-update.sh      # reuse an existing VM (skip provision)
#   SCENARIOS="S1 S2" ./e2e-auto-update.sh  # run a subset
#   TEST_FORK=you/yourfork ./e2e-auto-update.sh
#
set -euo pipefail

# --- Config ---
TEST_FORK="${TEST_FORK:-level09/bayanat-update-test}"
SSH_KEY="${SSH_KEY:-level09@Black09}"
SERVER_TYPE="${SERVER_TYPE:-cpx22}"
LOCATION="${LOCATION:-nbg1}"
SCENARIOS="${SCENARIOS:-S1 S2 S3 S4}"
KEEP_VM="${KEEP_VM:-0}"
VM_IP="${VM_IP:-}"
SERVER_NAME=""

SSHOPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5"

log()  { printf '\n\033[1;34m[%s] %s\033[0m\n' "$(date +%H:%M:%S)" "$*"; }
pass() { printf '\033[1;32m  ✓ %s\033[0m\n' "$*"; }
fail() { printf '\033[1;31m  ✗ %s\033[0m\n' "$*" >&2; exit 1; }

on_vm() { ssh $SSHOPTS "root@$VM_IP" "$@"; }

# --- Prereqs ---
command -v hcloud >/dev/null || { echo "hcloud CLI not found"; exit 2; }
command -v gh >/dev/null || { echo "gh CLI not found (needed to rewrite tags)"; exit 2; }
git ls-remote --tags "https://github.com/$TEST_FORK.git" >/dev/null \
    || { echo "test fork $TEST_FORK not reachable"; exit 2; }

# --- Tag ladder prep: hide upper tags so installer picks v4.0.0 ---
stash_upper_tags() {
    log "Hiding upper tags on $TEST_FORK so installer picks v4.0.0"
    for t in v4.0.1 v4.0.2 v4.0.3 v4.0.4; do
        gh api -X DELETE "repos/$TEST_FORK/git/refs/tags/$t" 2>&1 \
            | grep -v '^$' | head -1 || true
    done
}

restore_upper_tags() {
    log "Restoring upper tags v4.0.1..v4.0.4"
    # Must push via a configured remote (SSH auth), not an HTTPS URL.
    for t in v4.0.1 v4.0.2 v4.0.3 v4.0.4; do
        if ! git show-ref --tags --verify --quiet "refs/tags/$t"; then
            echo "  LOCAL TAG MISSING: $t (run the rebase block in the README)"; continue
        fi
        git push test-fork "+refs/tags/$t:refs/tags/$t" 2>&1 | tail -1
    done
    # Sanity: confirm remote has them
    local remote_tags
    remote_tags=$(git ls-remote --tags test-fork | awk '{print $2}' | grep -E 'v4\.0\.[1-4]$' | wc -l | tr -d ' ')
    [[ "$remote_tags" == "4" ]] || fail "expected 4 upper tags on remote, found $remote_tags"
    pass "4 upper tags visible on remote"
}

# --- Provision ---
provision() {
    SERVER_NAME="bayanat-update-test-$(date +%Y%m%d-%H%M%S)"
    log "Provisioning Hetzner VM $SERVER_NAME ($SERVER_TYPE in $LOCATION)"
    VM_IP=$(hcloud server create \
        --name "$SERVER_NAME" \
        --type "$SERVER_TYPE" \
        --image ubuntu-24.04 \
        --ssh-key "$SSH_KEY" \
        --location "$LOCATION" \
        -o json | python3 -c 'import json,sys; print(json.load(sys.stdin)["server"]["public_net"]["ipv4"]["ip"])')
    log "IP: $VM_IP"
    log "Waiting for SSH..."
    until on_vm 'true' 2>/dev/null; do sleep 3; done
    pass "SSH ready"
}

teardown() {
    if [[ "$KEEP_VM" == "1" ]]; then
        log "KEEP_VM=1 — leaving $SERVER_NAME (IP $VM_IP) alive"
        return
    fi
    if [[ -n "$SERVER_NAME" ]]; then
        log "Destroying $SERVER_NAME"
        hcloud server delete "$SERVER_NAME" >/dev/null
        pass "destroyed"
    fi
}

# --- Install ---
install_baseline() {
    log "Installing v4.0.0 via curl | sudo bash -s install (validates \$0-free install)"
    on_vm 'echo "BAYANAT_REPO='"$TEST_FORK"'" >> /etc/environment'
    on_vm 'curl -fsSL https://raw.githubusercontent.com/'"$TEST_FORK"'/v4.0.0/bayanat | BAYANAT_REPO='"$TEST_FORK"' sudo -E bash -s install localhost' \
        >/tmp/e2e-install.log 2>&1 \
        || { tail -30 /tmp/e2e-install.log; fail "install failed"; }
    pass "install succeeded"

    # Work around the SETUP_COMPLETE gating until that lands in installer
    on_vm 'echo "BAYANAT_CONFIG_FILE=/opt/bayanat/shared/config.json" >> /opt/bayanat/shared/.env
           echo "{\"SETUP_COMPLETE\": true}" > /opt/bayanat/shared/config.json
           chown bayanat:bayanat /opt/bayanat/shared/config.json
           systemctl restart bayanat bayanat-celery'
    sleep 3

    local health
    health=$(on_vm 'curl -s --unix-socket /opt/bayanat/current/bayanat.sock http://localhost/health')
    [[ "$health" == *'"status":"ok"'* ]] || fail "/health not ok: $health"
    pass "/health OK: $health"

    local cur
    cur=$(on_vm 'bayanat status | grep "Current version" | awk "{print \$3}"')
    [[ "$cur" == "v4.0.0" ]] || fail "expected v4.0.0, got $cur"
    pass "installed version: $cur"
}

# --- Scenario helpers ---
assert_version() {
    local expected="$1"
    local actual
    actual=$(on_vm 'bayanat status | grep "Current version" | awk "{print \$3}"')
    [[ "$actual" == "$expected" ]] || fail "expected version $expected, got $actual"
    pass "version = $expected"
}

assert_state() {
    local expected="$1"
    local actual
    actual=$(on_vm 'bayanat status | grep "Update state" | awk "{print \$3}"')
    [[ "$actual" == "$expected" ]] || fail "expected state $expected, got $actual"
    pass "update state = $expected"
}

assert_state_file_phase() {
    local expected="$1"
    local phase
    phase=$(on_vm 'python3 -c "import json; print(json.load(open(\"/opt/bayanat/state/update.json\")).get(\"phase\",\"\"))"' 2>/dev/null || echo "")
    [[ "$phase" == "$expected" ]] || fail "expected state file phase $expected, got '$phase'"
    pass "state file phase = $expected"
}

assert_services_active() {
    on_vm 'systemctl is-active --quiet bayanat bayanat-celery caddy' \
        || fail "services not all active"
    pass "services all active"
}

clear_state_file() {
    on_vm 'rm -f /opt/bayanat/state/update.json /opt/bayanat/state/update.lock'
}

run_update() {
    local tag="$1"
    log "  -> bayanat update $tag"
    on_vm 'sudo BAYANAT_REPO='"$TEST_FORK"' /usr/local/bin/bayanat update '"$tag" \
        >/tmp/e2e-update.log 2>&1 || true   # we inspect state, exit code is scenario-dependent
    tail -5 /tmp/e2e-update.log | sed 's/^/    /'
}

# --- Scenarios ---
S1() {
    log "S1: happy path v4.0.0 -> v4.0.1"
    run_update v4.0.1
    assert_version v4.0.1
    assert_state IDLE
    assert_services_active
    on_vm 'sudo -u bayanat psql -d bayanat -c "\d bulletin" | grep -q auto_update_test' \
        || fail "auto_update_test column missing"
    pass "auto_update_test column present"
}

S2() {
    log "S2: bad migration v4.0.1 -> v4.0.2 -> NEEDS_INTERVENTION"
    run_update v4.0.2
    assert_version v4.0.1
    assert_state_file_phase NEEDS_INTERVENTION
    assert_services_active
    clear_state_file
}

S3() {
    log "S3: bad /health v4.0.1 -> v4.0.3 -> ROLLED_BACK"
    run_update v4.0.3
    assert_version v4.0.1
    assert_state IDLE
    assert_services_active
    local health
    health=$(on_vm 'curl -s --unix-socket /opt/bayanat/current/bayanat.sock http://localhost/health')
    [[ "$health" == *'"status":"ok"'* ]] || fail "/health not ok after rollback"
    pass "/health back to OK after rollback"
}

S4() {
    log "S4: recovery v4.0.1 -> v4.0.4"
    run_update v4.0.4
    assert_version v4.0.4
    assert_state IDLE
    assert_services_active
    on_vm 'sudo -u bayanat psql -d bayanat -c "\d bulletin" | grep -q auto_update_recovery_test' \
        || fail "auto_update_recovery_test column missing"
    pass "auto_update_recovery_test column present"
}

# --- Main ---
trap 'restore_upper_tags; teardown' EXIT

if [[ -z "$VM_IP" ]]; then
    stash_upper_tags
    provision
    install_baseline
    restore_upper_tags
else
    log "Reusing existing VM at $VM_IP"
fi

for s in $SCENARIOS; do
    "$s"
done

log "ALL PASSED"

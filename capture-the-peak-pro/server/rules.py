"""
Capture the PEAK - progression, timer and scoring rules.

MODE switch:
  board  -> every stage open from the start, grouped by category
  linear -> stage N opens only once N-1 is solved

Hints are TIME-GATED. Hint tier t unlocks for free once the team has had the
camp open for t * HINT_STEP_MIN minutes. A team may force a hint open before
that, but each early reveal multiplies that camp's score by HINT_PENALTY.

The event clock is a single global wall-clock deadline (PEAK_END): every team
stops scoring at the same instant.
"""
import time

HINT_STEP_MIN = 10          # hint 1 free @10min, 2 @20min, 3 @30min
HINT_PENALTY = 0.7          # each hint forced early -> x0.7 on that camp


def stage_points(base_points, early_count):
    """Points a camp is worth given how many hints were force-revealed early."""
    base = int(base_points or 100)
    n = max(0, min(3, int(early_count or 0)))
    return int(round(base * (HINT_PENALTY ** n)))


# ---- hint time-gating -----------------------------------------------------
def hint_unlock_secs(tier):
    """Seconds after opening the camp before hint `tier` is free."""
    return int(tier) * HINT_STEP_MIN * 60


def hint_is_free(opened_epoch, tier):
    """Has enough time passed on this camp for hint `tier` to be free?"""
    if not opened_epoch:
        return False
    return (time.time() - float(opened_epoch)) >= hint_unlock_secs(tier)


def hint_free_in(opened_epoch, tier):
    """Seconds remaining until hint `tier` unlocks for free (0 if already)."""
    if not opened_epoch:
        return hint_unlock_secs(tier)
    left = hint_unlock_secs(tier) - (time.time() - float(opened_epoch))
    return max(0, int(left))


# ---- global event clock ---------------------------------------------------
def time_left(end_epoch):
    if not end_epoch:
        return 0.0
    return max(0.0, float(end_epoch) - time.time())


def is_locked(end_epoch, frozen=False):
    if frozen:
        return True
    if not end_epoch:
        return False
    return time.time() >= float(end_epoch)


# ---- availability ---------------------------------------------------------
def available(stage, mode, solved_set, n_stages):
    """Is `stage` playable right now for this team?"""
    if stage < 1 or stage > n_stages:
        return False
    if mode == "linear":
        if stage == 1:
            return True
        return (stage - 1) in solved_set
    return True   # board: everything open

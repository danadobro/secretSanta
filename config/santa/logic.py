import random
from typing import Dict, List, Optional, Set, Tuple

from .models import Event, Participant, Exclusion


def generate_secret_santa_matches(event: Event, *, max_attempts: int = 2000) -> Optional[Dict[Participant, Participant]]:
    """
    Returns a dict {giver_participant: receiver_participant} or None if impossible.

    Uses backtracking with heuristics:
    - assign givers with fewest options first
    - try receivers in random order (so it can find a solution even if one path fails)
    """
    participants: List[Participant] = list(event.participants.all())
    n = len(participants)
    if n < 4:
        return None

    # Build forbidden set of (giver_id, receiver_id)
    forbidden: Set[Tuple[int, int]] = set()
    for ex in Exclusion.objects.filter(event=event).values_list("giver_id", "excluded_id"):
        forbidden.add((ex[0], ex[1]))

    # Nobody can draw themselves
    for p in participants:
        forbidden.add((p.id, p.id))

    # Precompute allowed receivers for each giver
    allowed: Dict[int, List[int]] = {}
    ids = [p.id for p in participants]
    for giver_id in ids:
        options = [rid for rid in ids if (giver_id, rid) not in forbidden]
        allowed[giver_id] = options

    # Quick fail: if anyone has no options, impossible
    if any(len(opts) == 0 for opts in allowed.values()):
        return None

    id_to_participant = {p.id: p for p in participants}

    # Try multiple randomized attempts to avoid worst-case ordering issues
    for _ in range(max_attempts):
        # Givers sorted by fewest options first (MRV heuristic)
        givers = sorted(ids, key=lambda gid: len(allowed[gid]))

        used_receivers: Set[int] = set()
        assignment: Dict[int, int] = {}

        # Backtracking stack
        def backtrack(idx: int) -> bool:
            if idx == len(givers):
                return True

            giver = givers[idx]
            options = allowed[giver][:]

            # Prefer not-yet-used receivers, randomized for variety
            options = [r for r in options if r not in used_receivers]
            random.shuffle(options)

            for receiver in options:
                assignment[giver] = receiver
                used_receivers.add(receiver)

                if backtrack(idx + 1):
                    return True

                # undo
                used_receivers.remove(receiver)
                del assignment[giver]

            return False

        if backtrack(0):
            # Convert id mapping -> object mapping
            result = {id_to_participant[g]: id_to_participant[r] for g, r in assignment.items()}
            # sanity: must be perfect matching
            if len(result) == n and len({v.id for v in result.values()}) == n:
                return result

    return None

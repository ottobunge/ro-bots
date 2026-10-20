"""Pure population admission shared by direct factories and operator commands."""

MAX_ROSTER_AGENTS = 4096
MAX_FRIENDS_PER_GROUP = 16


def validate_population(
    n_groups: int, group_size_min: int, group_size_max: int, solos: int | None
) -> int:
    """Return solo count; ``n_groups`` includes solos, None retains legacy one.

    Validate worst-case membership, not randomly drawn sizes, before generation.
    Empty direct rosters remain valid; command admission requires nonempty ones.
    Friend-size policy applies even when every group is a solo.
    """
    _validate_integer_fields(n_groups, group_size_min, group_size_max, solos)
    solo_count = (1 if n_groups else 0) if solos is None else solos
    _validate_counts(n_groups, solo_count)
    _validate_friend_sizes(group_size_min, group_size_max)
    _validate_roster_bound(n_groups, solo_count, group_size_max)
    return solo_count


def _validate_integer_fields(
    n_groups: int, group_size_min: int, group_size_max: int, solos: int | None
) -> None:
    fields = {
        "n_groups": n_groups,
        "group_size_min": group_size_min,
        "group_size_max": group_size_max,
    }
    if solos is not None:
        fields["solos"] = solos
    for name, value in fields.items():
        if not isinstance(value, int) or isinstance(value, bool):
            msg = f"{name} must be an integer (not bool)"
            raise TypeError(msg)


def _validate_counts(n_groups: int, solo_count: int) -> None:
    if n_groups < 0 or not 0 <= solo_count <= n_groups:
        msg = "counts must satisfy 0 <= solos <= n_groups"
        raise ValueError(msg)


def _validate_friend_sizes(group_size_min: int, group_size_max: int) -> None:
    if group_size_min < 2 or group_size_min > group_size_max:
        msg = "friend sizes must satisfy 2 <= group_size_min <= group_size_max"
        raise ValueError(msg)
    if group_size_max > MAX_FRIENDS_PER_GROUP:
        msg = f"group_size_max must be <= {MAX_FRIENDS_PER_GROUP}"
        raise ValueError(msg)


def _validate_roster_bound(n_groups: int, solo_count: int, group_size_max: int) -> None:
    if (n_groups - solo_count) * group_size_max + solo_count > MAX_ROSTER_AGENTS:
        msg = f"maximum population must be <= {MAX_ROSTER_AGENTS}"
        raise ValueError(msg)

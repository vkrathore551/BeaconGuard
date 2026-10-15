
"""
BeaconGuard: THE LAST BEACON
Member 1 - Safe Route Algorithm

Features:
- 10x10 city grid
- Aarav and Mira starting positions
- Emergency beacon destination
- BFS shortest safe route
- Dynamic danger zones and blocked roads
- Zombie-horde rerouting
- Route validation and automated tests
"""

from collections import deque

# ============================================================
# 1. CITY CONFIGURATION
# ============================================================

GRID_SIZE = 10

# Coordinates use (row, column), starting from (0, 0).
FRIENDS = {
    "Aarav": (0, 0),
    "Mira": (9, 0),
}

BEACON = (5, 9)

DEFAULT_DANGER_ZONES = {
    (2, 2),
    (2, 3),
    (3, 3),
    (4, 6),
    (5, 6),
    (6, 6),
    (7, 4),
}

DEFAULT_BLOCKED_ROADS = set()


# ============================================================
# 2. GRID AND NEIGHBOR HELPERS
# ============================================================

def is_inside_grid(position, grid_size=GRID_SIZE):
    """Return True if a coordinate is inside the city grid."""
    if not isinstance(position, (tuple, list)) or len(position) != 2:
        return False

    row, col = position

    if not isinstance(row, int) or isinstance(row, bool):
        return False
    if not isinstance(col, int) or isinstance(col, bool):
        return False

    return 0 <= row < grid_size and 0 <= col < grid_size


def get_neighbors(position, grid_size=GRID_SIZE):
    """Return valid neighboring cells: up, down, left, and right."""
    row, col = position

    candidates = [
        (row - 1, col),
        (row + 1, col),
        (row, col - 1),
        (row, col + 1),
    ]

    return [
        cell for cell in candidates
        if is_inside_grid(cell, grid_size)
    ]


# ============================================================
# 3. BREADTH-FIRST SEARCH (BFS)
# ============================================================

def find_safe_route(
    start,
    destination=BEACON,
    danger_zones=None,
    blocked_roads=None,
    grid_size=GRID_SIZE,
):
    """
    Find the shortest safe route using BFS.

    Returns:
        A list of coordinates including start and destination,
        or None if no safe route exists.
    """

    if not is_inside_grid(start, grid_size):
        return None

    if not is_inside_grid(destination, grid_size):
        return None

    dangers = set(
        DEFAULT_DANGER_ZONES
        if danger_zones is None
        else danger_zones
    )

    blocked = set(
        DEFAULT_BLOCKED_ROADS
        if blocked_roads is None
        else blocked_roads
    )

    # Reject dangerous or blocked destinations and starts.
    if destination in dangers or destination in blocked:
        return None

    if start in dangers or start in blocked:
        return None

    if start == destination:
        return [start]

    queue = deque([start])
    parent = {start: None}

    while queue:
        current = queue.popleft()

        for neighbor in get_neighbors(current, grid_size):
            if neighbor in parent:
                continue

            if neighbor in dangers or neighbor in blocked:
                continue

            parent[neighbor] = current

            if neighbor == destination:
                # Reconstruct the shortest path.
                route = []
                cell = destination

                while cell is not None:
                    route.append(cell)
                    cell = parent[cell]

                route.reverse()
                return route

            queue.append(neighbor)

    # No safe path could be found.
    return None


# ============================================================
# 4. ROUTES FOR BOTH FRIENDS
# ============================================================

def find_routes_for_both_friends(
    danger_zones=None,
    blocked_roads=None,
    destination=BEACON,
    grid_size=GRID_SIZE,
):
    """Calculate an independent safe route for Aarav and Mira."""

    routes = {}

    for friend, position in FRIENDS.items():
        routes[friend] = find_safe_route(
            start=position,
            destination=destination,
            danger_zones=danger_zones,
            blocked_roads=blocked_roads,
            grid_size=grid_size,
        )

    return routes


# ============================================================
# 5. ROUTE VALIDATION
# ============================================================

def validate_route(
    route,
    start_position=None,
    destination=BEACON,
    danger_zones=None,
    blocked_roads=None,
    grid_size=GRID_SIZE,
    **kwargs,
):
    """
    Check that a route is safe, connected, and reaches its destination.

    Accepts start_position as a positional argument or start= keyword
    for compatibility with other project modules.
    """

    # Support the keyword used by some callers.
    if start_position is None:
        start_position = kwargs.pop("start", None)

    if kwargs:
        return False

    if not route or not isinstance(route, (list, tuple)):
        return False

    if start_position is None:
        start_position = route[0]

    dangers = set(
        DEFAULT_DANGER_ZONES
        if danger_zones is None
        else danger_zones
    )

    blocked = set(
        DEFAULT_BLOCKED_ROADS
        if blocked_roads is None
        else blocked_roads
    )

    if not is_inside_grid(start_position, grid_size):
        return False

    if not is_inside_grid(destination, grid_size):
        return False

    if route[0] != start_position or route[-1] != destination:
        return False

    for cell in route:
        if not is_inside_grid(cell, grid_size):
            return False

        if cell in dangers or cell in blocked:
            return False

    # Each consecutive step must move one cell horizontally or vertically.
    for index in range(1, len(route)):
        previous = route[index - 1]
        current = route[index]

        distance = (
            abs(previous[0] - current[0])
            + abs(previous[1] - current[1])
        )

        if distance != 1:
            return False

    return True


# ============================================================
# 6. CITY GRID DISPLAY
# ============================================================

def create_city_grid(
    routes=None,
    danger_zones=None,
    blocked_roads=None,
    grid_size=GRID_SIZE,
):
    """
    Create a printable grid.

    Symbols:
        A = Aarav
        M = Mira
        B = Beacon
        X = Danger zone
        # = Blocked road
        * = Safe route
        . = Open road
    """

    grid = [
        ["." for _ in range(grid_size)]
        for _ in range(grid_size)
    ]

    dangers = set(
        DEFAULT_DANGER_ZONES
        if danger_zones is None
        else danger_zones
    )

    blocked = set(
        DEFAULT_BLOCKED_ROADS
        if blocked_roads is None
        else blocked_roads
    )

    for row, col in dangers:
        if is_inside_grid((row, col), grid_size):
            grid[row][col] = "X"

    for row, col in blocked:
        if is_inside_grid((row, col), grid_size):
            grid[row][col] = "#"

    if routes:
        for route in routes.values():
            if route:
                for row, col in route:
                    if grid[row][col] == ".":
                        grid[row][col] = "*"

    # Place the beacon and friends last so their symbols remain visible.
    if is_inside_grid(BEACON, grid_size):
        grid[BEACON[0]][BEACON[1]] = "B"

    for friend, position in FRIENDS.items():
        row, col = position
        if is_inside_grid(position, grid_size):
            grid[row][col] = "A" if friend == "Aarav" else "M"

    return grid


def print_city_grid(grid):
    """Print the city grid with row and column labels."""

    print("    " + " ".join(str(col) for col in range(len(grid[0]))))
    print("   " + "--" * len(grid[0]))

    for row_index, row in enumerate(grid):
        print(f"{row_index:2} | " + " ".join(row))


# ============================================================
# 7. AUTOMATED TESTS
# ============================================================

def run_tests():
    """Run the main safe-route algorithm tests."""

    print("\nRunning safe-route tests...\n")

    # Test 1: Both friends should have safe routes.
    routes = find_routes_for_both_friends()

    for friend in FRIENDS:
        route = routes[friend]
        assert route is not None, f"{friend} should have a safe route."

        assert validate_route(
            route,
            FRIENDS[friend],
            BEACON,
        ), f"{friend}'s route should be valid."

    print("PASS: Both friends have valid safe routes.")

    # Test 2: A blocked road should be avoided.
    original_route = find_safe_route(FRIENDS["Aarav"])
    assert original_route is not None and len(original_route) > 2

    blocked_cell = original_route[1]

    new_route = find_safe_route(
        FRIENDS["Aarav"],
        blocked_roads={blocked_cell},
    )

    assert new_route is not None
    assert blocked_cell not in new_route

    print("PASS: The route avoids blocked roads.")

    # Test 3: A dangerous destination must be rejected.
    dangerous_destination = find_safe_route(
        FRIENDS["Aarav"],
        destination=(1, 1),
        danger_zones={(1, 1)},
    )

    assert dangerous_destination is None

    print("PASS: A dangerous destination is rejected.")

    # Test 4: No route exists when all starting exits are blocked.
    wall = {(0, 1), (1, 0)}

    no_route = find_safe_route(
        FRIENDS["Aarav"],
        blocked_roads=wall,
    )

    assert no_route is None

    print("PASS: None is returned when no route exists.")

    # Test 5: Invalid coordinates are rejected.
    assert find_safe_route((-1, 0)) is None
    assert find_safe_route((0, 0), destination=(10, 10)) is None

    print("PASS: Invalid coordinates are rejected.")

    print("\nALL SAFE-ROUTE TESTS PASSED!")


# ============================================================
# 8. ZOMBIE-HORDE REROUTING TEST
# ============================================================

def test_zombie_horde_rerouting():
    """
    Simulate a zombie horde blocking a cell on Aarav's original route.
    The algorithm must find a new route around that cell.
    """

    print("\nTesting zombie-horde rerouting...\n")

    original_route = find_safe_route(
        start=FRIENDS["Aarav"],
        destination=BEACON,
    )

    assert original_route is not None, (
        "Aarav needs an initial route for the simulation."
    )

    # Add the next cell in the original route to the danger zone.
    danger_zones = set(DEFAULT_DANGER_ZONES)

    if len(original_route) > 2:
        blocked_cell = original_route[1]
        danger_zones.add(blocked_cell)
    else:
        raise AssertionError("The original route is too short to test.")

    print(f"Zombie horde blocks cell: {blocked_cell}")

    # Recalculate the route after the horde appears.
    new_route = find_safe_route(
        start=FRIENDS["Aarav"],
        destination=BEACON,
        danger_zones=danger_zones,
    )

    assert new_route is not None, (
        "Aarav should find an alternative route."
    )

    assert blocked_cell not in new_route, (
        "The new route must avoid the zombie horde."
    )

    assert validate_route(
        new_route,
        FRIENDS["Aarav"],
        BEACON,
        danger_zones=danger_zones,
    ), "The alternative route must be valid."

    print("PASS: Zombie-horde rerouting test passed.")
    print(f"Original route length: {len(original_route) - 1} steps")
    print(f"Alternative route length: {len(new_route) - 1} steps")
    print("ALL ZOMBIE ROUTE TESTS PASSED!")


# ============================================================
# 9. RUN THE PROGRAM
# ============================================================

if __name__ == "__main__":
    print("=" * 55)
    print("BEACONGUARD: THE LAST BEACON")
    print("MEMBER 1 - SAFE ROUTE ALGORITHM")
    print("=" * 55)

    routes = find_routes_for_both_friends()

    for friend, route in routes.items():
        print(f"\n{friend}'s route:")

        if route:
            print(" -> ".join(str(cell) for cell in route))
            print(f"Steps required: {len(route) - 1}")
        else:
            print(f"No safe route available for {friend}.")

    print("\nCity grid:")
    print_city_grid(create_city_grid(routes=routes))

    run_tests()
    test_zombie_horde_rerouting()

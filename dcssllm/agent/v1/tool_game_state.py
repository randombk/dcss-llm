import json
from logging import getLogger
import typing
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

from dcssllm.agent.util import trim_indent
from dcssllm.agent.v1.tool import BaseTool

if typing.TYPE_CHECKING:
    from dcssllm.agent.v1.agent_main import V1Agent


logger = getLogger(__name__)

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set, Any


@dataclass
class Position:
    x: int
    y: int

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Position):
            return False
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))
    
    def __str__(self) -> str:
        return f"({self.x}, {self.y})"


@dataclass
class Cell:
    feature: str
    traversable: bool = False
    known: bool = False


@dataclass
class Monster:
    name: str
    position: Position


@dataclass
class Item:
    name: str
    position: Optional[Position] = None  # None for inventory items


class GameState:
    def __init__(self, filename: str = "tmp/llm_data.log"):
        # Player data
        self.player_pos: Optional[Position] = None
        self.player_health: Tuple[int, int] = (0, 0)  # current, max
        self.player_level: int = 0
        self.player_gold: int = 0
        self.turn_number: int = 0
        self.game_seed: int = 0

        # Items
        self.inventory: List[Item] = []
        self.equipment: List[Item] = []
        self.floor_items: List[Item] = []

        # Keys are Position objects, values are Cell objects
        self.map: Dict[Position, Cell] = {}
        self.map_size: Tuple[int, int] = (70, 80)  # (height, width) = (y, x)
        self.monsters: List[Monster] = []

        """Parse the llm_data.log file and populate the game state."""
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            logger.error(f"Error: Could not find {filename}")
            return

        current_section: Optional[str] = None

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check for section markers
            if line == "===SECTION===":
                current_section = None
                continue

            # Determine which section we're in
            if line.startswith("PLAYER_LOCATION:"):
                current_section = "player_data"
            elif line.startswith("PLAYER_INVENTORY"):
                current_section = "inventory"
            elif line.startswith("PLAYER_EQUIP"):
                current_section = "equipment"
            elif line.startswith("CURRENT_FLOOR_MAP"):
                current_section = "map"
            elif line.startswith("GAME_SEED:"):
                self.game_seed = int(line.split(": ")[1])

            # Process line based on current section
            if current_section == "player_data":
                self._parse_player_data(line)
            elif current_section == "inventory" and line.startswith("ITEM:"):
                item_name = line[6:].strip()
                self.inventory.append(Item(name=item_name))
            elif current_section == "equipment" and line.startswith("ITEM:"):
                item_name = line[6:].strip()
                self.equipment.append(Item(name=item_name))
            elif current_section == "map":
                self._parse_map_data(line)

    def _parse_player_data(self, line: str) -> None:
        """Parse player-related data lines."""
        if line.startswith("PLAYER_LOCATION:"):
            coords = line.split(": ")[1].split(",")
            x, y = int(coords[0]), int(coords[1])
            self.player_pos = Position(x, y)

        elif line.startswith("PLAYER_HEALTH:"):
            health_data = line.split(": ")[1].split("/")
            current, maximum = int(health_data[0]), int(health_data[1])
            self.player_health = (current, maximum)

        elif line.startswith("PLAYER_LEVEL:"):
            self.player_level = int(line.split(": ")[1])

        elif line.startswith("PLAYER_GOLD:"):
            self.player_gold = int(line.split(": ")[1])

        elif line.startswith("TURN_NUMBER:"):
            self.turn_number = int(line.split(": ")[1])

    def _parse_map_data(self, line: str) -> None:
        """Parse map-related data lines."""
        if line.startswith("CELL:"):
            # Format: CELL: x,y: feature_name[PATH][KNOWN]
            parts = line[6:].split(": ", 1)
            coords_str = parts[0]
            feature_info = parts[1]

            # Parse coordinates
            coords = coords_str.split(",")
            x, y = int(coords[0]), int(coords[1])

            # Parse feature and flags
            traversable = "[PATH]" in feature_info
            known = "[KNOWN]" in feature_info

            # Clean up feature name by removing flags
            feature = feature_info.replace("[PATH]", "").replace("[KNOWN]", "").strip()

            # Store in map
            self.map[Position(x, y)] = Cell(feature=feature, traversable=traversable, known=known)

        elif line.startswith("MONSTER:"):
            # Format: MONSTER: x,y: monster_name
            parts = line[9:].split(": ", 1)
            coords_str = parts[0]
            monster_name = parts[1]

            # Parse coordinates
            coords = coords_str.split(",")
            x, y = int(coords[0]), int(coords[1])

            # Add monster
            self.monsters.append(Monster(name=monster_name, position=Position(x, y)))

        elif line.startswith("ITEM:") and "," in line:  # Items on the floor have coordinates
            # Format: ITEM: x,y: item_name
            parts = line[6:].split(": ", 1)
            coords_str = parts[0]
            item_name = parts[1]

            # Parse coordinates
            coords = coords_str.split(",")
            x, y = int(coords[0]), int(coords[1])

            # Add item
            self.floor_items.append(Item(name=item_name, position=Position(x, y)))

    def get_cell(self, position: Position) -> Optional[Cell]:
        """Get the cell at the specified coordinates."""
        return self.map.get(position)

    def get_visible_area(self, view_radius: int = 8, require_knowledge: bool = True) -> List[List[Optional[Cell]]]:
        """Return a subset of the map that's visible to the player within the given radius."""
        if not self.player_pos:
            return None

        px, py = self.player_pos.x, self.player_pos.y

        # Calculate view boundaries
        min_x = max(0, px - view_radius)
        max_x = min(self.map_size[1] - 1, px + view_radius)
        min_y = max(0, py - view_radius)
        max_y = min(self.map_size[0] - 1, py + view_radius)

        # Create a 2D list for the visible area
        height = max_y - min_y + 1
        width = max_x - min_x + 1
        visible_area: List[List[Optional[Cell]]] = [[None for _ in range(width)] for _ in range(height)]

        # Fill the visible area with cells from the map
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                cell = self.get_cell(Position(x, y))
                if cell and ((not require_knowledge) or cell.known):
                    visible_area[y - min_y][x - min_x] = cell

        return visible_area

    def get_nearby_monsters(self, radius: int = 10) -> List[Tuple[Monster, float]]:
        """Return monsters near the player within the given radius."""
        if not self.player_pos:
            return []

        px, py = self.player_pos.x, self.player_pos.y
        nearby: List[Tuple[Monster, float]] = []

        for monster in self.monsters:
            mx, my = monster.position.x, monster.position.y
            distance = ((px - mx) ** 2 + (py - my) ** 2) ** 0.5
            if distance <= radius:
                nearby.append((monster, distance))

        return sorted(nearby, key=lambda x: x[1])  # Sort by distance

    def get_nearby_items(self, radius: int = 10) -> List[Tuple[Item, float]]:
        """Return items near the player within the given radius."""
        if not self.player_pos:
            return []

        px, py = self.player_pos.x, self.player_pos.y
        nearby: List[Tuple[Item, float]] = []

        for item in self.floor_items:
            ix, iy = item.position.x, item.position.y
            distance = ((px - ix) ** 2 + (py - iy) ** 2) ** 0.5
            if distance <= radius:
                nearby.append((item, distance))

        return sorted(nearby, key=lambda x: x[1])  # Sort by distance

    def get_player_summary(self) -> Dict[str, Any]:
        """Return a summary of player information."""
        hp_current, hp_max = self.player_health
        hp_percent = (hp_current / hp_max * 100) if hp_max > 0 else 0

        return {
            "position": self.player_pos,
            "health": f"{hp_current}/{hp_max} ({hp_percent:.1f}%)",
            "level": self.player_level,
            "gold": self.player_gold,
            "turn": self.turn_number,
            "inventory_count": len(self.inventory),
            "equipment_count": len(self.equipment)
        }

    def get_map_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Return the bounds of the explored map."""
        if not self.map:
            return None

        x_coords = [pos.x for pos in self.map.keys()]
        y_coords = [pos.y for pos in self.map.keys()]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        return (min_x, min_y, max_x, max_y)

    def get_map_section(self, min_pos: Position, max_pos: Position,
                        require_knowledge: bool = True) -> str:
        """Get a section of the map as a string representation."""
        ret = ""
        for y in range(min_pos.y, max_pos.y + 1):
            row = []
            for x in range(min_pos.x, max_pos.x + 1):
                cell = self.get_cell(Position(x, y))
                if cell and ((not require_knowledge) or cell.known):
                    char = "." if cell.traversable else "#"
                    if self.player_pos and x == self.player_pos.x and y == self.player_pos.y:
                        char = "@"
                    row.append(char)
                else:
                    row.append(" ")  # Unknown space
            ret += "".join(row) + "\n"
        return ret

    def get_map(self, require_knowledge: bool = True) -> str:
        """Get the complete map as a string representation."""
        map_bounds = self.get_map_bounds()
        return self.get_map_section(Position(map_bounds[0], map_bounds[1]), Position(map_bounds[2], map_bounds[3]),
                                    require_knowledge=require_knowledge)

    def get_summary_without_map(self) -> str:
        """Get a summary of the game state without the map."""
        return trim_indent(f"""
            Turn: {self.turn_number}
            Player: Level {self.player_level}, HP: {self.player_health[0]}/{self.player_health[1]}, Gold: {self.player_gold}
            Inventory: {len(self.inventory)} items
            Equipment: {len(self.equipment)} items
            Monsters visible: {len(self.get_nearby_monsters())}
            Items nearby: {len(self.get_nearby_items())}
        """)

    def get_delta_summary(self, previous: "GameState") -> str:
        """Write a brief summary of the differences between two game states, ignoring the map."""
        differences = []

        if self.turn_number != previous.turn_number:
            differences.append(f"Turn: {previous.turn_number} -> {self.turn_number}")
        if self.player_pos != previous.player_pos:
            differences.append(f"Player Position: {previous.player_pos} -> {self.player_pos}")

        hp_current, hp_max = self.player_health
        prev_hp_current, prev_hp_max = previous.player_health
        if hp_current != prev_hp_current or hp_max != prev_hp_max:
            differences.append(f"Player Health: {prev_hp_current}/{prev_hp_max} -> {hp_current}/{hp_max}")

        if self.player_level != previous.player_level:
            differences.append(f"Player Level: {previous.player_level} -> {self.player_level}")

        if self.player_gold != previous.player_gold:
            differences.append(f"Player Gold: {previous.player_gold} -> {self.player_gold}")

        if len(self.inventory) != len(previous.inventory):
            differences.append(f"Inventory: {len(previous.inventory)} items -> {len(self.inventory)} items")
            for item in self.inventory:
                if item not in previous.inventory:
                    differences.append(f"    Added {item.name}")
            for item in previous.inventory:
                if item not in self.inventory:
                    differences.append(f"    Removed {item.name}")

        if len(self.equipment) != len(previous.equipment):
            differences.append(f"Equipment: {len(previous.equipment)} items -> {len(self.equipment)} items")
            for item in self.equipment:
                if item not in previous.equipment:
                    differences.append(f"    Added {item.name}")
            for item in previous.equipment:
                if item not in self.equipment:
                    differences.append(f"    Removed {item.name}")

        if len(self.monsters) != len(previous.monsters):
            differences.append(f"Monsters: {len(previous.monsters)} -> {len(self.monsters)}")
            for monster in self.monsters:
                if monster not in previous.monsters:
                    differences.append(f"    Added {monster.name} at {monster.position}")
            for monster in previous.monsters:
                if monster not in self.monsters:
                    differences.append(f"    Removed {monster.name} at {monster.position}")

        if len(self.floor_items) != len(previous.floor_items):
            differences.append(f"Items on Floor: {len(previous.floor_items)} -> {len(self.floor_items)}")
            for item in self.floor_items:
                if item not in previous.floor_items:
                    differences.append(f"    Added {item.name} at {item.position}")
            for item in previous.floor_items:
                if item not in self.floor_items:
                    differences.append(f"    Removed {item.name} at {item.position}")

        if len(differences) == 0:
            return "No changes."

        return "\n".join(differences)

    def __str__(self) -> str:
        """Return a string representation of the game state."""
        summary = []
        summary.append(f"Game Seed: {self.game_seed}")
        summary.append(f"Turn: {self.turn_number}")

        if self.player_pos:
            hp_current, hp_max = self.player_health
            summary.append(f"Player: Level {self.player_level}, HP: {hp_current}/{hp_max}, Gold: {self.player_gold}")
            summary.append(f"Position: ({self.player_pos.x}, {self.player_pos.y})")

        summary.append(f"Inventory: {len(self.inventory)} items")
        summary.append(f"Equipment: {len(self.equipment)} items")
        summary.append(f"Map cells discovered: {len(self.map)}")
        summary.append(f"Monsters visible: {len(self.get_nearby_monsters())}")
        summary.append(f"Items nearby: {len(self.get_nearby_items())}")

        return "\n".join(summary)


class ToolGameState(BaseTool):
    def __init__(self, master: "V1Agent"):
        super().__init__(master)
        self.prev_state: Optional[GameState] = None
        self.current_state: Optional[GameState] = None

    def process_tool_call(self, tool_call: ChatCompletionMessageToolCall) -> None:
        pass

    def on_new_turn(self) -> None:
        self.prev_state = self.current_state
        self.current_state = GameState()

    def get_tool_description(self) -> List[Dict[str, Any]]:
        return []

    def get_state_diff_message(self) -> Optional[Dict[str, str]]:
        if not self.prev_state or not self.current_state:
            return None

        return {
            "role": "user",
            "content": "These things changed in the game state:\n\n" + self.current_state.get_delta_summary(self.prev_state)
        }

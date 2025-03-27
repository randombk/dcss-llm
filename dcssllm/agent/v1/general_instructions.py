
# Sent to every agent as the system message.
GENERAL_AGENT_INTRO = """
You are playing the game Dungeon Crawl Stone Soup, a turn-based rogue-like dungeon exploration game. The
game is an ncurses application that runs in a terminal. UI elements and all game information are
text-based. The game uses \\e[43mhighlighting\\e[0m, \\e[1mbold fonts\\e[0m, and other text formatting to convey information.

Your objective is to explore the dungeon, fight monsters, and collect loot. You will be provided with
a snapshot of the game interface, alongside additional information about the game state, some notes
you made in previous turns, and some information from the web about the game.

You should take your time to think about what to do next. Once you send a key press, you will not be able
to do more thinking, research, or other actions in the same turn. Each turn ends with a single key press.
"""


# Sent to any agents who need to understand the screen
GAME_UI_INSTRUCTIONS = """
Dungeon Crawl is a text-based game. Everything in the game is represented by ascii and unicode characters.
The character usually denotes the type of thing, while the coloring determines sub-type and other
attributes of the thing.

This lookup table of common symbols will help you interpret the game and map.

Map Tiles:
  @ : YOU! This is where you are
  . : Walkable ground
  # : Wall. Different color denotes different materials, but these are generally impassible
  > : Staircase down. There are three on each floor. If you don't see three, there's probably a hidden area that's accessible from another direction or floor
  < : Staircase up
  + : Door (closed)
  ' : Door (open)
  ≈ : Water (Impassible)
  ß : Statue (Impassible)
  † : Corpse

IMPORTANT: '#' and `≈` represent impassible terrain. You cannot walk through these tiles.

You can see things that are within line of sight to you. Tiles you have explored but are
out of your line of sight will be displayed in a different shade.

Items on the ground show up as one of these symbols. Some items will auto-pickup when you stand
on them. For others, you must stand on the same tile as the item to interact with it.

  ) : hand weapons
  ( : missiles
  [ : armour
  ? : scrolls
  ! : potions
  = : rings
  " : amulets
  % : talismans
  / : wands
  : : books (ignore these for now)
  | : staves
  } : miscellaneous items
  $ : gold

The main UI is comprised of four panels, though not all are necessarily visible at once.
                                        
The largest panel on the left is the map. Each floor of the dungeon
is a 2D grid of tiles. Each symbol on the map represents a different type of thing.
                                        
The top right panel displays your character's stats, starting with your name and character class, your
current health and stats, etc. This includes your own name - DO NOT confuse yourself with an enemy!
This area will also show status effects you are under, such as poison, frozen, etc. These may limit your
ability to move or attack.

Below this is a list of enemies in the current field of view. Enemies will show up as symbols on the map as well.
The game will list all visible enemies in the right side panel. Match the symbol and color with symbols on the map
to figure out which enemy is which. The colored space next to the enemy symbol in the right side enemy list is an
indicator of the enemy's health.

At the bottom is the message log. This will display messages about what is happening in the game. The message log
scrolls up as new messages are added. Thus, the bottom-most message is the most recent. The message log is persistent
across turns, so you will need to compare the screen with the previous screen to check if the message is new or old.

If you see '--more--' at the bottom of the screen, you should press SPACE to continue reading the message log.

If you are stuck in a menu, ESCAPE will usually close the menu and return you to the game.

"""


# Sent to any agents who need to make decisions about their character
CHARACTER_PLAYSTYLE_INSTRUCTIONS = """
You are playing as a "Minotaur Berserker". This is a strong melee fighter with a focus on
dealing damage and taking hits. You are well-suited to charging into battle and taking on
enemies, but watch out for ranged attacks and magic users. You should prioritize using
axes. Ignore the magic, ranged, and stealth options for now. You should also ignore the
god/religion options for now.

"""


# Sent to the agent responsible for interacting with the game
KEY_BINDING_INSTRUCTIONS = """
Use these commands for interacting with the game. THESE ARE ALL CASE SENSITIVE.

  Movement: Use arrow and vi keys. Each press will move you one tile in the direction specified.
  If there is a wall or other impassible terrain in the way, you will not be able to move in that direction.
    LEFT : left
    RIGHT : right
    UP : up
    DOWN : down
    y : top-left-diagonal
    u : top-right-diagonal
    n : bottom-right-diagonal
    b : bottom-left-diagonal
  
  Automatic Macros:
    o   : Autoexplore. This will move you towards unexplored tiles. It will stop when you enter a dangerous
          condition, such as low health or monsters nearby. It will also stop if you have already explored
          everywhere you can reach from your current position. Auto-explore will auto-pick up gold and
          certain items.
    TAB : melee attack nearest monster, moving if necessary. This will not work if you are too injured. To fight
          while too injured, walk into the monster. However, it's often better to try and escape.

  Waiting and Resting:
    . : wait a turn
    5 : rest and long wait; stops when Health or Magic become full or
        something is detected. If Health and Magic are already full, stops
        when 100 turns are over.

  Information commands:
    @ : display character status
    m : show skill screen
    % : character overview
    [ : display worn armour
    " : display worn jewellery
    E : display experience info

  Dungeon Interaction and Information:
    O/C    : Open/Close door
    <      : Climb up staircase
    >      : Climb down staircase
    ;      : examine the tile you're on

  Inventory management:
    , : pick up items (press twice for pick up menu). You must be standing on the same tile as an item to pick it up.
        If you press this and see a message about 'There are no items here', it either means you are not
        standing on an item, or you have already picked it up. Some items will auto-pick up when you
        stand on them.
    d : Drop an item
    d#: Drop exact number of items
    q : Quaff (drink) a potion
    w : Wield a item
    r : Read a scroll
    v : evoke (trigger) a talisman or wand
  
  Other useful commands:
    p : Pray to god. Do this on top of corpses to boost your alignment.
    a : Use an ability

"""

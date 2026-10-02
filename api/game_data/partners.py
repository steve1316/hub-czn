"""
Partner card data and related functions for CZN.
Contains partner definitions, stats, passives, and helper functions.
"""

# Default partner data for unknown partners
DEFAULT_PARTNER = {
    "name": "Unknown",
    "grade": 3,
    "class": "Controller",
    "passive_name": "Unknown Passive",
    "passive_desc": "Unknown passive effect.",
    "values": {},
    "stats": {},
    "ego_name": "Unknown Skill",
    "ego_cost": 2,
    "ego_desc": "Unknown effect.",
}

# Unified partner card data: res_id -> all partner information
# Contains: name, grade, class, passive_name, passive_desc, values, stats, ego_name, ego_cost, ego_desc
# Note: Values marked with # EST are estimated (linear interpolation) - update when real data is available
PARTNERS = {
    1025: {
        "name": "Ivy",
        "grade": 5,
        "class": "Psionic",
        "passive_name": "All of Me",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nWhen a 2-Cost or higher Justice-Attribute Attack Card of the assigned Combatant is activated, increase Damage Amount of the assigned Combatant's next Attack Card activated by {NextCardDMG%}%.\nIf a 2-, 3-, or 4-Cost Attack Card of the assigned Combatant is activated, gain 1 Premonition (max 1 time each).\nPremonition: Increase the assigned Combatant's Damage Amount by {PremonitionDMG%}% (max 3 stacks)",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "NextCardDMG%": (25, 32, 38, 44, 50),
            "PremonitionDMG%": (5, 7, 8, 9, 10),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "A New Visitor",
        "ego_cost": 3,
        "ego_desc": "TBD",
    },
    1058: {
        "name": "Solia",
        "grade": 5,
        "class": "Ranger",
        "passive_name": "Spacetime Warp",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\n+{ExtraDMG%}% Damage Amount to Extra Attacks dealt by the assigned Combatant.\nWhen the assigned combatant Draws for the first time each turn through an ability, +{CardDMG%}% Damage Amount to Attack Cards for 1 turn.",
        "values": {
            "ATK%": (12, 14, 16, 18, 20),
            "ExtraDMG%": (20, 25, 30, 35, 40),
            "CardDMG%": (10, 13, 15, 18, 20),
        },
        "stats": {"ATK%": (12, 14, 16, 18, 20)},
        "ego_name": "Spacetime Rift",
        "ego_cost": 3,
        "ego_desc": "250% Damage\nMark 1",
    },
    1070: {
        "name": "Aria",
        "grade": 5,
        "class": "Psionic",
        "passive_name": "Aria On Stage",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nIncrease Damage Amount of the assigned Combatant's Basic Attack Cards by {BasicAtkDMG%}% for each Basic Attack Card that shares the same name (max {MaxBasicAtkDMG%}%).\nWhen a Basic Attack Card is activated, the assigned Combatant gains 1 Swelling Melody.\nSwelling Melody: +{MelodyCDmg%}% Critical Damage to the assigned Combatant (max 4 stacks)",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "BasicAtkDMG%": (4, 5, 6, 7, 8),
            "MaxBasicAtkDMG%": (24, 30, 36, 42, 48),
            "MelodyCDmg%": (5, 7, 8, 9, 10),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "An Aria For You",
        "ego_cost": 2,
        "ego_desc": "+Basic Attack Card Damage\nIf Ego used: -1 Cost to Basic Attack Cards for 1 turn",
    },
    20001: {
        "name": "Arwen",
        "grade": 4,
        "class": "Controller",
        "passive_name": "Starshine Intellect",
        "passive_desc": "Increase the assigned Combatant's Health and Heal Amount by {HP%}%.\nAt the start of the turn, gain [Ponopoko's Cheer] for each enemy with an Anticipated Action in a Attack state.\n[Ponopoko's Cheer]: -{DR%}% Damage Amount taken\nOn effect activation, remove Ponopoko's Cheer (max 3 stacks)",
        "values": {
            "HP%": (8, 9, 10, 11, 12),
            "DR%": (10, 13, 15, 18, 20),
        },
        "stats": {"HP%": (8, 9, 10, 11, 12)},
        "ego_name": "Pokopo Ponpon!",
        "ego_cost": 3,
        "ego_desc": "Heal 200%. Apply 1 Damage Reduction.",
    },
    20002: {
        "name": "Gaya",
        "grade": 5,
        "class": "Controller",
        "passive_name": "Snow Upon the Heart",
        "passive_desc": "Increase the assigned Combatant's Defense by {DEF%}%.\n+{DEFDAM%}% Defense-Based Damage Amount to the assigned Combatant's Instinct cards.\nWhen using a Unique Attack Card of the assigned Combatant with an original Cost of 6, +{DMG%}% to Damage Amount of all allies (max 1).",
        "values": {
            "DEF%": (16, 18, 20, 22, 24),
            "DEFDAM%": (20, 25, 30, 35, 40),
            "DMG%": (20, 25, 30, 35, 40),
        },
        "stats": {"DEF%": (16, 18, 20, 22, 24)},
        "ego_name": "Ice Wyrm's Roar",
        "ego_cost": 3,
        "ego_desc": "60% Defense-Based Damage x 4.\nDraw 1 Attack Card(s).",
    },
    20003: {
        "name": "Alyssa",
        "grade": 4,
        "class": "Controller",
        "passive_name": "Alchemical Fruits",
        "passive_desc": "The assigned combatant's Defense is increased by {DEF%}%.\nAt the end of battle, recover {heal}% Health.",
        "values": {
            "DEF%": (12, 15, 18, 21, 24),
            "heal": (3, 3.8, 4.5, 5.3, 6),
        },
        "stats": {"DEF%": (12, 15, 18, 21, 24)},
        "ego_name": "Vitality Boosting Potion",
        "ego_cost": 2,
        "ego_desc": "Heal 100%. When in an Injured state, increase Healing Amount by 50%. 1 Morale for 1 turn.",
    },
    20004: {
        "name": "Janet",
        "grade": 5,
        "class": "Hunter",
        "passive_name": "Understanding and Ideas",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\n+{CRate%}% Critical Chance to 1-Cost or lower Attack Cards of the assigned Combatant.\nWhen the assigned Combatant activates 5 Bullet cards, create a random Handgun Bullet card. Increase Damage Amount of the created card by {CreatedCardDMG%}%.",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "CRate%": (9, 12, 14, 16, 18),
            "CreatedCardDMG%": (50, 88, 125, 163, 200),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Ultimate Missile Turret!",
        "ego_cost": 3,
        "ego_desc": "TBD",
    },
    20005: {
        "name": "Eishlen",
        "grade": 5,
        "class": "Vanguard",
        "passive_name": "Arcane Wave",
        "passive_desc": "The assigned combatant's Health and shield gain are increased by {HP%}%.\nWhen the assigned Combatant gains Counterattack for the first time, +{Counter%}%.",
        "values": {
            "HP%": (8, 10, 12, 14, 16),
            "Counter%": (15, 19, 23, 27, 30),
        },
        "stats": {"DEF%": (12, 14, 16, 18, 20), "HP%": (12, 14, 16, 18, 20)},
        "ego_name": "Innos's Guardian",
        "ego_cost": 4,
        "ego_desc": "100% shield. At the end of the turn, retain 50% of Shield.",
    },
    20006: {
        "name": "Nyx",
        "grade": 5,
        "class": "Controller",
        "passive_name": "Resonance",
        "passive_desc": "The assigned combatant's HP and healing are increased by {HP%}%.\nWhen the assigned combatant Draws for the first time each turn using an ability, {DMG%}% Damage dealt by allies for 1 turn.",
        "values": {
            "HP%": (8, 10, 12, 14, 16),
            "DMG%": (8, 10, 12, 14, 16),
        },
        "stats": {"DEF%": (12, 14, 16, 18, 20), "HP%": (12, 14, 16, 18, 20)},
        "ego_name": "Errante Hurricane",
        "ego_cost": 4,
        "ego_desc": "Discard up to 3 cards, then Draw +1 cards equal to the number discarded.",
    },
    20007: {
        "name": "Akad",
        "grade": 4,
        "class": "Hunter",
        "passive_name": "Self Defense",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nIncrease Damage Amount of the assigned Combatant's Bullet cards by {BulletDMG%}%.\nWhen the assigned Combatant lands a Critical Hit for the first time, increase Damage of Bullet cards by {BulletDMG2%}% for 1 turn.",
        "values": {
            "ATK%": (8, 10, 12, 14, 16),
            "BulletDMG%": (10, 13, 15, 18, 20),
            "BulletDMG2%": (12, 15, 18, 21, 24),
        },
        "stats": {"ATK%": (8, 10, 12, 14, 16)},
        "ego_name": "What I Wished to Protect",
        "ego_cost": 2,
        "ego_desc": "For 1 turn, +25% Critical Chance of Designated Combatants's Attack cards.",
    },
    20008: {
        "name": "Anteia",
        "grade": 5,
        "class": "Psionic",
        "passive_name": "Clairvoyance",
        "passive_desc": "The assigned combatant's HP and damage are increased by {HP%}%.\nWhen a card is created for the first time by the assigned Combatant each turn, +{CardDMG%}% Damage Amount to Attack Cards for 1 turn.",
        "values": {
            "HP%": (8, 10, 12, 14, 16),
            "CardDMG%": (8, 10, 12, 14, 16),
        },
        "stats": {"ATK%": (12, 14, 16, 18, 20), "HP%": (12, 14, 16, 18, 20)},
        "ego_name": "Scholarly Measures",
        "ego_cost": 2,
        "ego_desc": "180% Damage to all enemies. 1 Vulnerable.",
    },
    20009: {
        "name": "Zeta",
        "grade": 5,
        "class": "Vanguard",
        "passive_name": "Deadly Poison",
        "passive_desc": "Increase the assigned Combatant's Defense by {DEF%}%.\nIncrease Defense-Based Damage Amount of the assigned Combatant's Instinct Cards by {InstinctDEFDAM%}%.\n+{CelestialBonus%}% Defense-Based Damage and Shield Gain Amounts to the assigned Combatant's Celestial cards",
        "values": {
            "DEF%": (16, 18, 20, 22, 24),
            "CelestialBonus%": (25, 32, 38, 44, 50),
            "InstinctDEFDAM%": (15, 19, 23, 27, 30),
        },
        "stats": {"DEF%": (16, 18, 20, 22, 24)},
        "ego_name": "Undertaking the Mission",
        "ego_cost": 2,
        "ego_desc": "200% Defense-Based Damage. Draws 1 highest-cost card.",
    },
    20010: {
        "name": "Nakia",
        "grade": 3,
        "class": "Ranger",
        "passive_name": "Hot-Blooded Soldier",
        "passive_desc": "The assigned combatant's Attack is increased by {ATK%}%.\nWhen an ally defeats an enemy, gain 1 [Backline Support].\n[Backline Support]: {DMG%}% Damage of 1 attack card. Upon activation, Backline Support is reduced by 1 (up to 3 stacks).",
        "values": {
            "ATK%": (8, 10, 12, 14, 16),
            "DMG%": (10, 13, 15, 18, 20),
        },
        "stats": {
            "ATK%": (8, 10, 12, 14, 16),
        },
        "ego_name": "Powerful Shot",
        "ego_cost": 2,
        "ego_desc": "Deal 200% Damage.",
    },
    20011: {
        "name": "Daisy",
        "grade": 4,
        "class": "Ranger",
        "passive_name": "Dowsing",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nIncrease Damage Amount of the assigned Combatant's Extra Attacks by {Extra DMG%}%.\nWhen the assigned Combatant Draws for the first time each turn using an ability, has a {MChance%}% chance to gain 1 Morale for 1 turn.",
        "values": {
            "ATK%": (8, 10, 12, 14, 16),
            "Extra DMG%": (10, 13, 15, 18, 20),
            "MChance%": (20, 25, 30, 35, 40),
        },
        "stats": {"ATK%": (8, 10, 12, 14, 16)},
        "ego_name": "Commencing Detection!",
        "ego_cost": 2,
        "ego_desc": "Gain 180% Shield. Gain 1 Morale for 1 turn.",
    },
    20012: {
        "name": "Zatera",
        "grade": 3,
        "class": "Psionic",
        "passive_name": "Fortune Telling",
        "passive_desc": "The assigned combatant's Attack is increased by {ATK%}%.\nWhen Injured, at the end of battle, recover {skill}% Health.",
        "values": {
            "ATK%": (8, 10, 12, 14, 16),
            "skill": (4, 5, 6, 7, 8),
        },
        "stats": {"ATK%": (8, 10, 12, 14, 16)},
        "ego_name": "Flower of Memory",
        "ego_cost": 2,
        "ego_desc": "Gain 200% Shield.",
    },
    20013: {
        "name": "Raidel",
        "grade": 3,
        "class": "Vanguard",
        "passive_name": "Strategic Analysis",
        "passive_desc": "The combatant's max Health increases by {HP%}%.\nIf the combatant is in Counterattack state, their Defense-Based Damage increases by {DEFDAM%}%.",
        "values": {
            "HP%": (8, 10, 12, 14, 16),
            "DEFDAM%": (8, 10, 12, 14, 16),
        },
        "stats": {"HP%": (8, 10, 12, 14, 16)},
        "ego_name": "Analyze Weakness",
        "ego_cost": 2,
        "ego_desc": "Gain 100% Shield. Gain 1 Counterattack.",
    },
    20014: {
        "name": "Serithea",
        "grade": 5,
        "class": "Hunter",
        "passive_name": "Ensemble",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\n+{CRate%}% Critical Chance to the assigned Combatant's Attack Cards.\n+{CDmg%}% Critical Damage when the assigned Combatant's Attack Card inflicts a Critical Hit. Can stack up to 5 times.",
        "values": {
            "ATK%": (12, 14, 16, 18, 20),
            "CRate%": (8, 10, 12, 14, 16),
            "CDmg%": (3, 3.5, 4, 4.5, 5),
        },
        "stats": {"ATK%": (12, 14, 16, 18, 20)},
        "ego_name": "Crimson Romance",
        "ego_cost": 3,
        "ego_desc": "250% Damage. 2 Vulnerable.",
    },
    20015: {
        "name": "Douglas",
        "grade": 3,
        "class": "Striker",
        "passive_name": "Guard",
        "passive_desc": "The assigned combatant's Attack is increased by {ATK%}%.\nAt the start of battle, Damage dealt by the assigned combatant increases by {DMG%}% for 1 turn.",
        "values": {
            "ATK%": (8,10,12,14,16),
            "DMG%": (8,10,12,14,16),
        },
        "stats": {"ATK%": (8,10,12,14,16)
        },
        "ego_name": "Giant Bazooka",
        "ego_cost": 2,
        "ego_desc": "120% Damage to all enemies",
    },
    20016: {
        "name": "Yuri",
        "grade": 3,
        "class": "Hunter",
        "passive_name": "Cantrip",
        "passive_desc": "The assigned combatant's Attack is increased by {ATK%}%.\nUpon the first shuffle, the assigned combtant's damage dealt is increased by {DMG%}%.",
        "values": {
            "ATK%": (8,10,12,14,16),
            "DMG%": (8,10,12,14,16)
        },
        "stats": {"ATK%": (8,10,12,14,16)},
        "ego_name": "Drone Deployment",
        "ego_cost": 3,
        "ego_desc": "Draw 2",
    },
    20019: {
        "name": "Priscilla",
        "grade": 5,
        "class": "Striker",
        "passive_name": "Arachnid Domain",
        "passive_desc": "The assigned combatant's HP and damage are increased by {HP%}%.\n+{RavagedDMG%}% Damage dealt by the assigned Combatant to targets in a Ravaged state.",
        "values": {
            "HP%": (8, 10, 12, 14, 16),
            "RavagedDMG%": (25, 32, 38, 44, 50),
        },
        "stats": {"ATK%": (12, 14, 16, 18, 20), "HP%": (12, 14, 16, 18, 20)},
        "ego_name": "Arachnid Web",
        "ego_cost": 2,
        "ego_desc": "Deal 250% Damage. Apply Weakness Attack to 1 assigned combatant's random Attack cards in hand.",
    },
    20021: {
        "name": "Bria",
        "grade": 5,
        "class": "Psionic",
        "passive_name": "Check the instructions",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nWhen the assigned Combatant creates a card, gain Risk Factor Report\nRisk Factor Report: Increase Damage Amount of the assigned Combatant's Attack Cards by {RFR%}% for 1 turn (max 3 stacks)\nWhen the assigned Combatant creates a Status Ailment card for the first time (includes cards that have been changed from Status Ailment cards), +{AilmentDMG%}% Damage Amount to Attack Cards for 1 turn.",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "RFR%": (10, 13, 15, 18, 20),
            "AilmentDMG%": (25, 32, 38, 44, 50),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Capable Secretary",
        "ego_cost": 3,
        "ego_desc": "Exhaust all Status Ailment cards (including those changed from Status Ailment) and Curse cards in the Discard Pile. Increase Damage Amount of the assigned combatant's Attack Cards by X% for each card Exhausted for 1 turn.",
    },
    20023: {
        "name": "Blanche",
        "grade": 5,
        "class": "Vanguard",
        "passive_name": "Blood Detection",
        "passive_desc": "The assigned combatant's Defense is increased by {DEF%}%.\nEach time the assigned combatant Draws a 2-Cost or higher card, gain {Shield%}% Shield.",
        "values": {
            "DEF%": (18, 21, 24, 27, 30),
            "Shield%": (25, 32, 38, 44, 50),
        },
        "stats": {"DEF%": (18, 21, 24, 27, 30)},
        "ego_name": "Here's a shot!",
        "ego_cost": 3,
        "ego_desc": "TBD",
    },
    20024: {
        "name": "Wilhelmina",
        "grade": 4,
        "class": "Vanguard",
        "passive_name": "Battle Command",
        "passive_desc": "Increase the assigned Combatant's Defense by {DEF%}%.\n+{DEFDAM%}% Defense-Based Damage Amount to the assigned Combatant's Attack Cards against targets in a Vulnerable state.",
        "values": {
            "DEF%": (12, 15, 18, 21, 24),
            "DEFDAM%": (10, 13, 15, 18, 20),
        },
        "stats": {"DEF%": (12, 15, 18, 21, 24)},
        "ego_name": "Tactical Command",
        "ego_cost": 2,
        "ego_desc": "For 1 turn, gain 2 Morale.\nFor 1 turn, gain 1 Fortitude.",
    },
    20025: {
        "name": "Rosaria",
        "grade": 4,
        "class": "Ranger",
        "passive_name": "Financial Support",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nIncrease Damage Amount of the assigned Combatant's Extra Attacks by {Extra DMG}%.\nWhen the assigned Combatant activates an Upgrade or Skill Card, has a {MChance%}% chance to gain 1 Morale for 1 turn.",
        "values": {
            "ATK%": (8, 10, 12, 14, 16),
            "Extra DMG": (10, 13, 15, 18, 20),
            "MChance%": (25, 32, 38, 44, 50),
        },
        "stats": {"ATK%": (8, 10, 12, 14, 16)},
        "ego_name": "Security Team, Requesting Support!",
        "ego_cost": 2,
        "ego_desc": "Draw 1 Enhanced Card(s).\nIf there are no Enhance Cards in the Draw Pile, Draw 1 Card.",
    },
    20026: {
        "name": "Yvonne",
        "grade": 3,
        "class": "Controller",
        "passive_name": "Bless",
        "passive_desc": "Increase the assigned Combatant's Defense by {DEF%}%.\nWhen the assigned Combatant does not activate an Attack Card by the end of the turn, Heal {heal%}% to recover Health at the start of the next turn.",
        "values": {
            "DEF%": (8, 10, 12, 14, 16),
            "heal%": (30, 38, 45, 53, 60),
        },
        "stats": {"DEF%": (8, 10, 12, 14, 16)},
        "ego_name": "Consecration",
        "ego_cost": 2,
        "ego_desc": "Heal 100%. For 1 turn, gain 1 Fortitude.",
    },
    20027: {
        "name": "Eloise",
        "grade": 4,
        "class": "Psionic",
        "passive_name": "Technical Support",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nIncrease Damage Amount of the assigned Combatant's Attack Cards by {atkcard%}%.\nThe first time the assigned Combatant either Exhausts a card or gains a Status Ailment card (includes cards that have been changed from Status Ailment cards), increases Damage Amount of Attack Cards by {atkcard%2}% for 1 turn.",
        "values": {
            "ATK%": (8, 10, 12, 14, 16),
            "atkcard%": (10, 13, 15, 18, 20),
            "atkcard%2": (12, 15, 18, 21, 24),
        },
        "stats": {"ATK%": (8, 10, 12, 14, 16)},
        "ego_name": "Activate Defense Module",
        "ego_cost": 3,
        "ego_desc": "For 1 turn, when a card is Exhausted, apply 1 Weaken to a random enemy.",
    },
    20030: {
        "name": "Kiara",
        "grade": 5,
        "class": "Hunter",
        "passive_name": "Analyze Weakness",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nWhen 10 or more cards are in the Graveyard, increase Damage Amount of the assigned Combatant's Attack Cards by {GraveDMG%}%.\nWhen a card is Discarded for the first time by the assigned Combatant each turn, +{DiscardDMG%}% Damage Amount to Attack Cards for 1 turn.",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "GraveDMG%": (15, 19, 23, 27, 30),
            "DiscardDMG%": (25, 32, 38, 44, 50),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Lumina Explosion",
        "ego_cost": 3,
        "ego_desc": "200% Damage. +20% Damage by the number of cards in Graveyard.",
    },
    20032: {
        "name": "Rachel",
        "grade": 4,
        "class": "Vanguard",
        "passive_name": "Replenish Energy",
        "passive_desc": "The assigned combatant's skill card shield gain is increased by {shieldgain%}%.\nWhen the assigned combatant gains Shield, {counterchance%}% chance to gain 1 Counterattack.",
        "values": {
            "shieldgain%": (10, 13, 15, 18, 20),
            "counterchance%": (20, 25, 30, 35, 40),
        },
        "stats": {},
        "ego_name": "Colonel Hamburger!",
        "ego_cost": 2,
        "ego_desc": "Gain 100% Shield. Draw 1 Card.",
    },
    20033: {
        "name": "Lillian",
        "grade": 4,
        "class": "Striker",
        "passive_name": "Poltergeist",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\n+{atkDAM%}% Damage Amount to 1-Cost or lower Attack Cards of the assigned Combatant.\nWhen the assigned combatant activates a Skill card, +{atkDAM%2}% Damage Amount to Attack Cards for 1 turn. Stacks up to 3 times.",
        "values": {
            "ATK%": (8, 10, 12, 14, 16),
            "atkDAM%": (10, 13, 15, 18, 20),
            "atkDAM%2": (10, 13, 15, 18, 20),
        },
        "stats": {"ATK%": (8, 10, 12, 14, 16)},
        "ego_name": "Light of Judgement",
        "ego_cost": 3,
        "ego_desc": "Deal 100% Damage to all enemies. Draw 1 Attack card(s) from the assigned combatant with cost of less than or equal to 1.",
    },
    20034: {
        "name": "Scarlet",
        "grade": 5,
        "class": "Striker",
        "passive_name": "The Path to Mastery",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nIf the assigned Combatant's card was activated just before, +{ConsecutiveDMG%}% Damage Amount to Attack Cards. Can stack up to 2 times and is removed when a different Combatant's card is activated.\nEach time 2 of the assigned Combatant's cards are activated, gain Focus.\nFocus: Increase Damage Amount of the assigned Combatant's Attack Cards by {FocusDMG%}%\nOn effect activation, decrease Focus by 1, and when another Combatant's card is activated, remove Focus",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "ConsecutiveDMG%": (15, 19, 23, 27, 30),
            "FocusDMG%": (20, 25, 30, 35, 40),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Binding Knot",
        "ego_cost": 3,
        "ego_desc": "X% Damage. +X% assigned combatant's Attack Card Damage Amount for each owned buff for 1 turn.",
    },
    20035: {
        "name": "Ritochka",
        "grade": 4,
        "class": "Striker",
        "passive_name": "Construction Support",
        "passive_desc": "The assigned Combatant's attack cards with a cost of 2 or more deal +{Cost2DMG%}% damage.\nAt the start of the turn, 1 of the assigned Combatant's attack cards gains +{CostScaleDMG%}% damage for every point of the total cost of attack cards.",
        "values": {
            "Cost2DMG%": (10, 13, 15, 18, 20),
            "CostScaleDMG%": (5, 7, 8, 9, 10),
        },
        "stats": {"ATK%": (8, 10, 12, 14, 16)},
        "ego_name": "Workplace hazards ahead!",
        "ego_cost": 2,
        "ego_desc": "For 1 turn, 3 Morale.",
    },
    20036: {
        "name": "Carroty",
        "grade": 4,
        "class": "Hunter",
        "passive_name": "Super Carrot Power!",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nAt the start of the turn, increase Damage Amount of 1 Attack Card of the assigned Combatant by {cardATK%}%.\nWhen the assigned Combatant creates a card for the first time, increase Damage Amount of Attack Cards by {cardATK%2}% for 1 turn.",
        "values": {
            "ATK%": (8, 10, 12, 14, 16),
            "cardATK%": (10, 13, 15, 18, 20),
            "cardATK%2": (10, 13, 15, 18, 20),
        },
        "stats": {"ATK%": (8, 10, 12, 14, 16)},
        "ego_name": "Eating Soft Carrots",
        "ego_cost": 2,
        "ego_desc": "Increase Damage Amount of cards created by Designated Combatants's ability by 20% for 1 turn.",
    },
    20037: {
        "name": "Marianne",
        "grade": 5,
        "class": "Striker",
        "passive_name": "Eyes on the Target",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nIncrease Damage Amount dealt by the assigned Combatant to targets in a Ravage state by {RavagedDMG%}%.\nAlways apply the assigned Combatant's Basic Cards as Weakness Damage, and +{WeaknessDMG%}% Weakness Damage Amount",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "RavagedDMG%": (15, 19, 23, 27, 30),
            "WeaknessDMG%": (5, 10, 15, 20, 25),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Blood Stalker",
        "ego_cost": 3,
        "ego_desc": "TBD",
    },
    20038: {
        "name": "Tina",
        "grade": 5,
        "class": "Ranger",
        "passive_name": "Communication Support",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nIncrease Damage Amount of Order Attribute Extra Attacks by {OrderExtraDMG%}%.\n+{TargetExtra%}% Damage Amount to Extra Attacks activated through Targeting Attack Cards.",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "TargetExtra%": (25, 32, 38, 44, 50),
            "OrderExtraDMG%": (15, 19, 23, 27, 30),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Target confirmed, initiating support!",
        "ego_cost": 2,
        "ego_desc": "Draw 1. Increase the combatant's Extra Attack damage by 30% for 1 turn.",
    },
    30044: {
        "name": "Westmacott",
        "grade": 5,
        "class": "Striker",
        "passive_name": "Gleaming Deduction",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nWhen an Attack Card of the assigned Combatant is Drawn through that Combatant's ability, +{DrawnDMG%}% Damage Amount to that card for 1 turn.\nIncrease Damage Amount of the assigned Combatant's cards that have Inspiration by {InspirationDMG%}%.",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "DrawnDMG%": (25, 32, 38, 44, 50),
            "InspirationDMG%": (20, 25, 30, 35, 40),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Clue Spotted",
        "ego_cost": 3,
        "ego_desc": "Move 1 card from hand to Draw Pile. Draw 1 assigned Combatant cards.",
    },
    30045: {
        "name": "Asteria",
        "grade": 5,
        "class": "Striker",
        "passive_name": "Starshine-piercing Lighthouse",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\n+{HighCostDMG%}% Damage Amount to base 2-Cost or higher Attack Cards of the assigned Combatant.\nIncrease Damage Amount of the assigned Combatant's Pulverize cards by {PulverizeDMG%}%.",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "HighCostDMG%": (30, 38, 45, 53, 60),
            "PulverizeDMG%": (20, 25, 30, 35, 40),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Light of Ark",
        "ego_cost": 2,
        "ego_desc": "+20% Damage of the next Attack card used by the assigned Combatant for the total cost of all cards in the hand (Max 10).",
    },
    30046: {
        "name": "Itsuku",
        "grade": 5,
        "class": "Psionic",
        "passive_name": "Tranquil Marker",
        "passive_desc": "The assigned combatant's Attack is increased by {ATK%}%. Every time the assigned Combatant's cards stack, increases Damage Amount of Attack Cards by {StackDMG%}%. Can stack up to 3 times.\nEvery time 1 Attack Card used by the assigned Combatant deals 3 Hits, inflicts {FixedDMG%}% Fixed Damage to the target.",
        "values": {
            "ATK%": (8, 10, 12, 14, 16),
            "StackDMG%": (5, 7, 8, 9, 10),
            "FixedDMG%": (30, 38, 45, 53, 60),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Moonlit Leisure",
        "ego_cost": 4,
        "ego_desc": "200% Damage to all enemies.\n 1 Fierce Winds.",
    },
    30051: {
        "name": "Marin",
        "grade": 5,
        "class": "Ranger",
        "passive_name": "Raging Wave",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nIncrease Damage Amount of Extra Attacks of cards created by the assigned Combatant's abilities by {ExtraDMG%}%.\nWhen the assigned Combatant activates a Skill Card for the first time each turn, +{SkillExtra%}% Damage Amount to Extra Attacks for 1 turn.",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "ExtraDMG%": (15, 19, 23, 27, 30),
            "SkillExtra%": (25, 32, 38, 44, 50),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Azure Fury",
        "ego_cost": 3,
        "ego_desc": "200% Damage to all enemies. Draw 1 skill card.",
    },
    30052: {
        "name": "Noel",
        "grade": 5,
        "class": "Controller",
        "passive_name": "Hymn of Blessing",
        "passive_desc": "Increase the assigned Combatant's Defense by {DEF%}%.\nIncrease Damage, Shield Gain, and Heal Amounts of the assigned Combatant's Retain cards by {RetainBonus%}%.\nAt the end of the turn, deal Fixed Damage to all enemies equal to {FixedDMG%}% for each retained card of the assigned combatant. +5% Damage for enemies with the Instinct attribute.",
        "values": {
            "DEF%": (16, 18, 20, 22, 24),
            "RetainBonus%": (15, 19, 23, 27, 30),
            "FixedDMG%": (15, 19, 23, 27, 30),
        },
        "stats": {"DEF%": (16, 18, 20, 22, 24)},
        "ego_name": "Legato of Faith",
        "ego_cost": 3,
        "ego_desc": "Heal 100%. Activate the Retain effect of all cards held by the assigned combatant.",
    },
    30053: {
        "name": "Sophia",
        "grade": 5,
        "class": "Hunter",
        "passive_name": "Milky Way Chorus",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nWhen a Passion Quietus card of the assigned Combatant is Discarded, +{CDmg%}% Critical Damage (max 4 stacks).\nWhen 3 Bullet cards are Discarded, the assigned Combatant performs a {ExtraAtk%}% Extra Attack on a random enemy (2 times per turn).",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "CDmg%": (5, 7, 8, 9, 10),
            "ExtraAtk%": (200, 250, 300, 350, 400),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Always Cheer For You",
        "ego_cost": 3,
        "ego_desc": "Apply X Die-hard Fan to the assigned combatant. Draw X. Discard up to X cards in hand.",
    },
    30054: {
        "name": "Erica",
        "grade": 5,
        "class": "Vanguard",
        "passive_name": "No Speeding!",
        "passive_desc": "Increase the assigned Combatant's Defense by {DEF%}%.\nIncrease Damage Amount of the assigned Combatant's Counterattacks by {CounterDMG%}%.\nWhen the assigned Combatant activates a Skill or Upgrade Card, has a {CounterChance%}% chance to gain Counterattack.",
        "values": {
            "DEF%": (16, 18, 20, 22, 24),
            "CounterDMG%": (15, 19, 23, 27, 30),
            "CounterChance%": (50, 63, 75, 88, 100),
        },
        "stats": {"DEF%": (16, 18, 20, 22, 24)},
        "ego_name": "Crackdown Beam Bombardment",
        "ego_cost": 2,
        "ego_desc": "200% Defense-based Damage to all enemies.\n1 Counterattack.\nIf any enemy's Anticipated Action is attack, 1 Counterattack.",
    },
    30076: {
        "name": "Peko",
        "grade": 5,
        "class": "Hunter",
        "passive_name": "Peko's Multi-Purpose Kit",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nWhen the assigned Combatant's card Moves from the Graveyard to hand, gain 1 Repairs Complete.\nRepairs Complete: +{RepairsDMG%}% Damage Amount to the assigned Combatant's Attack Cards (Max-3) \nIncrease Damage Amount of the assigned Combatant's Attack Cards that are used against Ravaged targets by {RavagedDMG%}%.",
        "values": {
            "ATK%": (8, 10, 12, 14, 16),
            "RepairsDMG%": (10, 13, 15, 18, 20),
            "RavagedDMG%": (15, 19, 23, 27, 30),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Overclock Beacon",
        "ego_cost": 3,
        "ego_desc": "When an ally inflicts Ravage, 1 Overclock to the assigned Combatant (1 per turn).",
    },
    30085: {
        "name": "Tiana",
        "grade": 5,
        "class": "Controller",
        "passive_name": "Star in the Darkness",
        "passive_desc": "Increase the assigned Combatant's Defense by {DEF%}%.\nWhen the assigned Combatant creates 3 Exhaust cards, increase Damage Amount of the next Attack Card of allies activated by {AllyDMG%}% (max 2stacks).\nWhen the assigned Combatant has activated both Shield Gain and Heal through Order Cards, +{AllyCRate%}% Critical Chance to allies for 1 turn (cannot stack).",
        "values": {
            "DEF%": (16, 18, 20, 22, 24),
            "AllyDMG%": (15, 19, 23, 27, 30),
            "AllyCRate%": (6, 8, 9, 11, 12),
        },
        "stats": {"DEF%": (16, 18, 20, 22, 24)},
        "ego_name": "Phase Alignment",
        "ego_cost": 3,
        "ego_desc": "TBD",
    },
    30091: {
        "name": "Alcea",
        "grade": 5,
        "class": "Vanguard",
        "passive_name": "You're Quite High Maintenance",
        "passive_desc": "Increase the assigned Combatant's Defense by {DEF%}%.\nWhen an Exhaust card of the assigned Combatant is Exhausted or activated, increase Defense-Based Damage Amount of the next Attack Card used by {DEFDAM%}% (max 1-stack).\nWhen a 2-Cost or higher card of the assigned Combatant is Exhausted, gain {FixedShield%}% Fixed Shield (1 time per turn).",
        "values": {
            "DEF%": (8, 10, 12, 14, 16),
            "DEFDAM%": (20, 25, 30, 35, 40),
            "FixedShield%": (100, 125, 150, 175, 200),
        },
        "stats": {"DEF%": (16, 18, 20, 22, 24)},
        "ego_name": "If You Require Assistance",
        "ego_cost": 3,
        "ego_desc": "250% Defense-Based Damage.\n5 Caustic Remarks.",
    },
    30094: {
        "name": "Sylvia",
        "grade": 5,
        "class": "Ranger",
        "passive_name": "Auroric Wingbeats",
        "passive_desc": "The assigned combatant's Attack is increased by {ATK%}%.\nEach time the assigned combatant's Linked cards are used manually or Discarded, gain 1 Zephyr.\n[Zephyr]: +{ZephyrDMG%}% Damage Amount to the assigned combatant's Passion Attack Cards (max 3 stacks).\nWhen Zephyr reaches 3 stacks, +{ZephyrCDmg%}% Critical Damage to the assigned combatant.",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "ZephyrDMG%": (15, 19, 23, 27, 30),
            "ZephyrCDmg%": (20, 25, 30, 35, 40),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Field Overview",
        "ego_cost": 2,
        "ego_desc": "Select up to 2 cards in hand and apply Linked. If a selected card is the assigned combatant's Linked card, +X% Critical Damage to the assigned combatant for each such card instead.",
    },
    30095: {
        "name": "Clara",
        "grade": 5,
        "class": "Vanguard",
        "passive_name": "Dreamwoven Prism",
        "passive_desc": "Increase the assigned Combatant's Defense by {DEF%}%.\nWhen a card with the Blessing effect applied by the assigned Combatant is used, Fixed Heal {Heal%}% (5 times per turn).\nWhen the assigned Combatant's Blessing card is used, allies gain 1 Prism.\n[Prism]: Increase Damage Amount of Attack Cards and Shield Gain Amount of Skill Cards by {PrismDMG%}% (max 4 stacks).",
        "values": {
            "DEF%": (16, 18, 20, 22, 24),
            "Heal%": (40, 45, 50, 55, 60),
            "PrismDMG%": (5, 7, 8, 9, 10),
        },
        "stats": {"DEF%": (16, 18, 20, 22, 24)},
        "ego_name": "Genius Stage Director",
        "ego_cost": 3,
        "ego_desc": "200% Shield\nDraw 2 Blessing cards from Draw Pile.",
    },
    30116: {
        "name": "Licinia",
        "grade": 5,
        "class": "Striker",
        "passive_name": "Poison-Laced Atonement",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nWhen Fracture is applied through an ability of the assigned Combatant, +{CRate}% to Critical Chance (cannot stack).\nWhen Fracture is activated through an ability of the assigned Combatant, inflict 1 Virutoxin on the target.\n[Virutoxin]: Increase Damage Amount taken from the assigned Combatant by {VirutoxinDMG%}% (max 4 stacks).",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "CRate": (10, 13, 15, 18, 20),
            "VirutoxinDMG%": (4, 5, 6, 7, 8),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "Blossoming Venom",
        "ego_cost": 3,
        "ego_desc": "Gain 1 AP\n3 Paralytic Poison to all enemies.",
    },
    30118: {
        "name": "Emilie",
        "grade": 5,
        "class": "Psionic",
        "passive_name": "As My Mistress Wishes",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nWhen Fracture is inflicted through a card of the assigned Combatant, +{CRate}% to Critical Chance and increase Damage Amount of ally Fracture and Scorched by {AllyDMG%}% (cannot stack).",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "CRate": (10, 13, 15, 18, 20),
            "AllyDMG%": (15, 19, 23, 27, 30),
        },
        "stats": {"ATK%": (16, 18, 20, 22, 24)},
        "ego_name": "For My Mistress",
        "ego_cost": 2,
        "ego_desc": "300 Damage\n2 Sensory Deprivation",
    },
    30092: {
        "name": "Ruixiang",
        "grade": 5,
        "class": "Ranger",
        "passive_name": "A Pleasant Aroma Lingers",
        "passive_desc": "Increase the assigned Combatant's Attack by {ATK%}%.\nEach time the assigned Combatant creates a Void-Attribute Attack Card in Draw Pile, gain 1 Gentle Aroma.\nWhen Gentle Aroma reaches 5 stacks, +{CDmg%}% Critical Damage to the assigned Combatant.\nGentle Aroma: +{AromaDMG%}% Damage Amount to the assigned Combatant (max 5 stacks)",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "CDmg%": (20, 25, 30, 35, 40),
            "AromaDMG%": (5, 7, 8, 9, 10),
        },
        "stats": {
            "ATK%": (16, 18, 20, 22, 24),
        },
        "ego_name": "Incense",
        "ego_cost": 3,
        "ego_desc": "Draw 1 of the assigned Combatant's Attack Card\nIf Cost of that card is either 0 or X, Draw 2",
    },
    30114: {
        "name": "Eunie",
        "grade": 5,
        "class": "Ranger",
        "passive_name": "Battlefield Saturation Doctrine",
        "passive_desc": "Increase Attack of the assigned Combatant by {ATK%}%.\nWhen the assigned Combatant creates an Instinct-Attribute Attack Card in Draw Pile, increase Damage Amount of the Extra Attack of that card by {ExtraDMG%}% until activated.\nIf that card is an Unusable card, gain 1 Preparing Live Rounds.\nPreparing Live Rounds: +{CRate%}% Critical Chance to the assigned Combatant (cannot stack)",
        "values": {
            "ATK%": (16, 18, 20, 22, 24),
            "ExtraDMG%": (40, 50, 60, 70, 80),
            "CRate%": (10, 13, 15, 18, 20),
        },
        "stats": {
            "ATK%": (16, 18, 20, 22, 24),
        },
        "ego_name": "Lay Down Suppressive Fire!",
        "ego_cost": 3,
        "ego_desc": "80 Damage to all enemies\n1 Leaving the Rest to You!, and when an enemy is defeated, 1 Ammo Transfer for each defeated",
    },
}

# Base stats by grade and class at level 60
# Offensive classes (Hunter, Psionic, Ranger, Striker): High ATK, low DEF
# Defensive classes (Controller, Vanguard): Low ATK, high DEF
# Per-partner base stats at max level (level 60), sourced from game DB
# (cumulative level group bonus + default_stat_add)
PARTNER_BASE_STATS: dict[int, dict] = {
    1025:  {"atk": 145, "def": 0,  "hp": 119},
    1058:  {"atk": 89,  "def": 0,  "hp": 80},
    20001: {"atk": 0,   "def": 35, "hp": 70},
    20002: {"atk": 0,   "def": 51, "hp": 119},
    20003: {"atk": 0,   "def": 35, "hp": 70},
    20004: {"atk": 118, "def": 0,  "hp": 119},
    20005: {"atk": 0,   "def": 39, "hp": 80},
    20006: {"atk": 0,   "def": 39, "hp": 80},
    20007: {"atk": 80,  "def": 0,  "hp": 70},
    20008: {"atk": 89,  "def": 0,  "hp": 80},
    20009: {"atk": 0,   "def": 51, "hp": 119},
    20010: {"atk": 71,  "def": 0,  "hp": 60},
    20011: {"atk": 80,  "def": 0,  "hp": 70},
    20012: {"atk": 71,  "def": 0,  "hp": 60},
    20013: {"atk": 0,   "def": 31, "hp": 60},
    20014: {"atk": 89,  "def": 0,  "hp": 80},
    20015: {"atk": 71,  "def": 0,  "hp": 60},
    20016: {"atk": 71,  "def": 0,  "hp": 60},
    20019: {"atk": 89,  "def": 0,  "hp": 80},
    20021: {"atk": 118, "def": 0,  "hp": 119},
    20023: {"atk": 0,   "def": 39, "hp": 80},
    20024: {"atk": 0,   "def": 35, "hp": 70},
    20025: {"atk": 80,  "def": 0,  "hp": 70},
    20026: {"atk": 0,   "def": 31, "hp": 60},
    20027: {"atk": 80,  "def": 0,  "hp": 70},
    20030: {"atk": 118, "def": 0,  "hp": 119},
    20032: {"atk": 0,   "def": 35, "hp": 70},
    20033: {"atk": 80,  "def": 0,  "hp": 70},
    20034: {"atk": 118, "def": 0,  "hp": 119},
    20035: {"atk": 80,  "def": 0,  "hp": 70},
    20036: {"atk": 80,  "def": 0,  "hp": 70},
    20037: {"atk": 118, "def": 0,  "hp": 119},
    20038: {"atk": 118, "def": 0,  "hp": 119},
    30044: {"atk": 118, "def": 0,  "hp": 119},
    30045: {"atk": 118, "def": 0,  "hp": 119},
    30046: {"atk": 145, "def": 0,  "hp": 119},
    30051: {"atk": 118, "def": 0,  "hp": 119},
    30052: {"atk": 0,   "def": 51, "hp": 119},
    30053: {"atk": 118, "def": 0,  "hp": 119},
    30054: {"atk": 0,   "def": 51, "hp": 119},
    30076: {"atk": 118, "def": 0,  "hp": 119},
    30085: {"atk": 0,   "def": 51, "hp": 119},
    30091: {"atk": 0,   "def": 51, "hp": 119},
    30094: {"atk": 118, "def": 0,  "hp": 119},
}

# Fallback estimates by (grade, class) for partners not yet in PARTNER_BASE_STATS
PARTNER_CLASS_STATS = {
    (3, "Hunter"):     {"atk": 71,  "def": 0,  "hp": 60},
    (3, "Psionic"):    {"atk": 71,  "def": 0,  "hp": 60},
    (3, "Ranger"):     {"atk": 71,  "def": 0,  "hp": 60},
    (3, "Striker"):    {"atk": 71,  "def": 0,  "hp": 60},
    (3, "Controller"): {"atk": 0,   "def": 31, "hp": 60},
    (3, "Vanguard"):   {"atk": 0,   "def": 31, "hp": 60},
    (4, "Hunter"):     {"atk": 80,  "def": 0,  "hp": 70},
    (4, "Psionic"):    {"atk": 80,  "def": 0,  "hp": 70},
    (4, "Ranger"):     {"atk": 80,  "def": 0,  "hp": 70},
    (4, "Striker"):    {"atk": 80,  "def": 0,  "hp": 70},
    (4, "Controller"): {"atk": 0,   "def": 35, "hp": 70},
    (4, "Vanguard"):   {"atk": 0,   "def": 35, "hp": 70},
    (5, "Hunter"):     {"atk": 118, "def": 0,  "hp": 119},
    (5, "Psionic"):    {"atk": 118, "def": 0,  "hp": 119},
    (5, "Ranger"):     {"atk": 118, "def": 0,  "hp": 119},
    (5, "Striker"):    {"atk": 118, "def": 0,  "hp": 119},
    (5, "Controller"): {"atk": 0,   "def": 51, "hp": 119},
    (5, "Vanguard"):   {"atk": 0,   "def": 51, "hp": 119},
}


# Per-partner fixed flat stat additions sourced from partner_base@char_partner.json.
# These are applied unconditionally on top of the level-scaled base stats.
# Key: res_id (int), Value: {"atk": int, "def": int, "hp": int}
PARTNER_DEFAULT_ADD: dict[int, dict] = {
    20001: {"atk": 0,  "def": 6,  "hp": 0},
    20002: {"atk": 0,  "def": 9,  "hp": 1},
    20003: {"atk": 0,  "def": 6,  "hp": 0},
    20004: {"atk": 27, "def": 0,  "hp": 1},
    20005: {"atk": 0,  "def": 7,  "hp": 0},
    20006: {"atk": 0,  "def": 7,  "hp": 0},
    20007: {"atk": 16, "def": 0,  "hp": 0},
    20008: {"atk": 19, "def": 0,  "hp": 0},
    20009: {"atk": 0,  "def": 9,  "hp": 1},
    20010: {"atk": 13, "def": 0,  "hp": 0},
    20011: {"atk": 16, "def": 0,  "hp": 0},
    20012: {"atk": 13, "def": 0,  "hp": 0},
    20013: {"atk": 0,  "def": 5,  "hp": 0},
    20014: {"atk": 19, "def": 0,  "hp": 0},
    20015: {"atk": 13, "def": 0,  "hp": 0},
    20016: {"atk": 13, "def": 0,  "hp": 0},
    20019: {"atk": 19, "def": 0,  "hp": 0},
    20021: {"atk": 27, "def": 0,  "hp": 1},
    20023: {"atk": 0,  "def": 7,  "hp": 0},
    20024: {"atk": 0,  "def": 6,  "hp": 0},
    20025: {"atk": 16, "def": 0,  "hp": 0},
    20026: {"atk": 0,  "def": 5,  "hp": 0},
    20027: {"atk": 16, "def": 0,  "hp": 0},
    20030: {"atk": 27, "def": 0,  "hp": 1},
    20032: {"atk": 0,  "def": 6,  "hp": 0},
    20033: {"atk": 16, "def": 0,  "hp": 0},
    20034: {"atk": 27, "def": 0,  "hp": 1},
    20035: {"atk": 16, "def": 0,  "hp": 0},
    20036: {"atk": 16, "def": 0,  "hp": 0},
    20037: {"atk": 27, "def": 0,  "hp": 1},
    20038: {"atk": 27, "def": 0,  "hp": 1},
    30044: {"atk": 27, "def": 0,  "hp": 1},
    30045: {"atk": 27, "def": 0,  "hp": 1},
    1058:  {"atk": 19, "def": 0,  "hp": 0},
    30051: {"atk": 27, "def": 0,  "hp": 1},
    30052: {"atk": 0,  "def": 9,  "hp": 1},
    30054: {"atk": 0,  "def": 9,  "hp": 1},
    30046: {"atk": 27, "def": 0,  "hp": 1},
    30076: {"atk": 27, "def": 0,  "hp": 1},
    30085: {"atk": 0,  "def": 9,  "hp": 1},
    30091: {"atk": 0,  "def": 9,  "hp": 1},
    1025:  {"atk": 27, "def": 0,  "hp": 1},
    30053: {"atk": 27, "def": 0,  "hp": 1},
    30094: {"atk": 27, "def": 0,  "hp": 1},
    30092: {"atk": 27, "def": 0, "hp": 1},
    30114: {"atk": 27, "def": 0, "hp": 1},
}


def get_partner(res_id: int) -> dict:
    """Get partner data by res_id, returning DEFAULT_PARTNER if not found."""
    return PARTNERS.get(res_id, DEFAULT_PARTNER)


def get_value_for_ego_level(values_tuple: tuple, limit_break: int) -> float:
    """Get the value from a 5-element tuple based on limit_break (0-4)."""
    if not values_tuple or len(values_tuple) < 5:
        return 0
    index = max(0, min(4, limit_break))  # Clamp to 0-4
    return values_tuple[index]


def get_partner_base_stats(res_id: int) -> dict:
    """Get base stats for a partner card at max level (60), sourced from game DB."""
    if res_id in PARTNER_BASE_STATS:
        return PARTNER_BASE_STATS[res_id]
    partner = get_partner(res_id)
    grade = partner.get("grade", 3)
    partner_class = partner.get("class", "Controller")
    return PARTNER_CLASS_STATS.get((grade, partner_class), {"atk": 0, "def": 0, "hp": 0})


def get_partner_stats(res_id: int, level: int) -> dict:
    """Calculate partner card stats based on level.
    Stats scale linearly from base values to max at level 60, then
    default_atk_add / default_def_add / default_hp_add from partner_base
    are added unconditionally (these are fixed per-partner flat bonuses
    loaded from partner_base@char_partner.json)."""
    base = get_partner_base_stats(res_id)
    scale = level / 60.0
    # Per-partner default flat additions from partner_base@char_partner.json.
    # These are independent of level and ascend.
    default_add = PARTNER_DEFAULT_ADD.get(res_id, {"atk": 0, "def": 0, "hp": 0})
    return {
        "atk": int(base["atk"] * scale) + default_add["atk"],
        "def": int(base["def"] * scale) + default_add["def"],
        "hp": int(base["hp"] * scale) + default_add["hp"],
    }


# SSSR-tier partners: HP+6 per ascend step, no ATK/DEF gain
SSSR_ASCEND_PARTNERS = {
    1025, 20002, 20004, 20009, 20021, 20030, 20034, 20037, 20038,
    30044, 30045, 30046, 30051, 30052, 30053, 30054, 30076, 30085, 30091, 30094,
    30092,
    30114,
}


def get_partner_ascend_bonus(res_id: int, ascend: int) -> dict:
    """Get cumulative flat stat bonus from partner ascension (ascend 0-5).
    SSSR partners give HP+6 per step with no ATK/DEF gain.
    Other partners give ATK+1, DEF+1, HP+5 per step (dev_ascend group)."""
    level = max(0, min(5, ascend))
    if res_id in SSSR_ASCEND_PARTNERS:
        return {"atk": 0, "def": 0, "hp": level * 6}
    return {"atk": level, "def": level, "hp": level * 5}


def get_partner_passive_stats(res_id: int, limit_break: int) -> dict:
    """Get unconditional passive stat bonuses for a partner card.
    Returns stat bonuses based on limit_break (0=E0 through 4=E4)."""
    partner = get_partner(res_id)
    stats = {}
    for stat_name, values_tuple in partner.get("stats", {}).items():
        stats[stat_name] = get_value_for_ego_level(values_tuple, limit_break)
    return stats


def format_passive_description(res_id: int, limit_break: int) -> str:
    """Format the passive description with values based on limit_break."""
    partner = get_partner(res_id)

    desc = partner.get("passive_desc", "Unknown passive effect.")
    values = partner.get("values", {})

    # Replace each placeholder with the value for this ego level
    for placeholder, values_tuple in values.items():
        current_val = get_value_for_ego_level(values_tuple, limit_break)
        # Format as integer if whole number, otherwise one decimal
        if current_val == int(current_val):
            val_str = str(int(current_val))
        else:
            val_str = f"{current_val:.1f}"
        desc = desc.replace("{" + placeholder + "}", val_str)

    return desc


def get_partner_passive_info(res_id: int, limit_break: int) -> dict:
    """Get full passive information for display.
    Returns dict with passive_name, formatted description, ego_name, ego_cost, ego_desc."""
    partner = get_partner(res_id)

    return {
        "passive_name": partner.get("passive_name", "Unknown"),
        "passive_desc": format_passive_description(res_id, limit_break),
        "ego_name": partner.get("ego_name", "Unknown"),
        "ego_cost": partner.get("ego_cost", 0),
        "ego_desc": partner.get("ego_desc", "Unknown effect."),
    }
import json
import requests
import re


class Weapon:
    def __init__(
        self,
        *,
        name="Generic",
        category="PRIMARY",
        compat="RIFLE",
        cc=0.2,
        cd=2.0,
        fire_rate=8,
        mag=40,
        rel=2,
        imp=10,
        punc=10,
        slash=10,
        element=0,
    ):
        self.name = name
        self.category = category
        self.compat = compat
        self.cc = cc
        self.cd = cd
        self.fire_rate = fire_rate
        self.mag = mag
        self.reload = rel
        self.imp = imp
        self.punc = punc
        self.slash = slash
        self.element = element

    def __str__(self):
        return self.name

    def ips(self):  # Physical damage distribution
        total = self.imp + self.punc + self.slash + self.element
        return [self.imp / total, self.punc / total, self.slash / total]


WEAPONS_URL = "https://wf.snekw.com/weapons-wiki"
r = requests.get(url=WEAPONS_URL)
weapon_data = r.json()
weapon_data = weapon_data["data"]["Weapons"]

arsenal = {}

for item in weapon_data:
    weapon = weapon_data[item]

    # TODO: Archguns
    if weapon["Type"] in ["Primary", "Secondary"]:

        # TODO: Bows and other charged weapons
        if "Trigger" in weapon and weapon["Trigger"] in ["Charge", "Burst / Charge"]:
            continue

        # Fill in missing values

        ips = []
        for damage_type in ["Impact", "Puncture", "Slash"]:
            if damage_type not in weapon["NormalAttack"]["Damage"]:
                weapon["NormalAttack"]["Damage"][damage_type] = 0
            ips.append(weapon["NormalAttack"]["Damage"][damage_type])

        if "CritChance" not in weapon["NormalAttack"]:
            weapon["NormalAttack"]["CritChance"] = 0

        if "CritMultiplier" not in weapon["NormalAttack"]:
            weapon["NormalAttack"]["CritMultiplier"] = 1

        # Regulators have a listed reload time for some reason
        if weapon["Name"].startswith("Regulators"):
            weapon["Magazine"] = 100
            weapon["Reload"] = 0

        # There are no mods limited to a certain type of secondary
        if weapon["Type"] == "Secondary":
            weapon["Class"] = "PISTOL"

        # Create the weapon
        arsenal[weapon["Name"].lower()] = Weapon(
            name=weapon["Name"],
            category=weapon["Type"].upper(),
            compat=weapon["Class"].upper(),
            cc=weapon["NormalAttack"]["CritChance"],
            cd=weapon["NormalAttack"]["CritMultiplier"],
            fire_rate=weapon["NormalAttack"]["FireRate"],
            mag=weapon["Magazine"],
            rel=weapon["Reload"],
            imp=ips[0],
            punc=ips[1],
            slash=ips[2],
            element=sum(weapon["NormalAttack"]["Damage"].values()) - sum(ips),
        )

regular_compats = ["PRIMARY", "RIFLE", "SHOTGUN", "PISTOL", "ASSAULT RIFLE", "SNIPER"]


class Mod:
    def __init__(self, name="Generic"):
        self.name = name
        self.compat = "NONE"
        self.conditional = False
        self.damage = 0
        self.multishot = 0
        self.critical_chance = 0
        self.critical_damage = 0
        self.element = 0
        self.impact = 0
        self.puncture = 0
        self.slash = 0
        self.fire_rate = 0
        self.magazine_capacity = 0
        self.reload_speed = 0

    def __bool__(self):
        return self.stats() != [0] * len(self.stats())

    def __lt__(self, other):

        left = self
        right = other

        # Exceptions for sorting
        if self.name == "Blaze":
            left = Mod()
            left.damage = 0.6
            left.element = 0.61
        elif self.name == "Heavy Caliber":
            left = Mod()
            left.damage = 1.54

        if other.name == "Blaze":
            right = Mod()
            right.damage = 0.6
            right.element = 0.61
        elif other.name == "Heavy Caliber":
            right = Mod()
            right.damage = 1.64

        left_max = max(left.stats())
        left_index = left.stats().index(left_max)
        right_max = max(right.stats())
        right_index = right.stats().index(right_max)

        if left_index != right_index:
            return (
                left_index > right_index
            )  # Order by main stat importance (Multishot > Slash etc)
        elif left_max != right_max:
            return left_max < right_max  # Order by main stat value
        else:
            return sum(left.stats()) < sum(
                right.stats()
            )  # Order by total amount of stats provided

    # DPS relevant stat names
    def stat_names(self):
        return list(self.__dict__.keys())[3:]

    # DPS relevant stat values
    def stats(self):
        return list(self.__dict__.values())[3:]

    # Increase stat by keyword
    def increase(self, stat, amount):
        self.__setattr__(stat, self.__getattribute__(stat) + amount)


class Modlist:
    def __init__(self):
        self.mods = []

    def __getitem__(self, key):
        if type(key) == int:
            return self.mods[key]
        else:
            found = [mod for mod in self.mods if mod.name == key]
            if found:
                return found[0]
            else:
                return None

    def get(self, weapon):

        # Shotguns and pistols only have one compat
        if weapon.compat in ["SHOTGUN", "PISTOL"]:
            mods = [mod for mod in self.mods if mod.compat == weapon.compat]

        else:  # The rest are rifles
            mods = [
                mod
                for mod in self.mods
                if (
                    mod.compat.endswith("RIFLE")
                    or (mod.compat == "SNIPER" and weapon.compat == "SNIPER RIFLE")
                )
            ]

        ## Vigilante mods fit in all primaries
        if weapon.category == "PRIMARY":
            mods.extend([mod for mod in self.mods if mod.name.startswith("Vigilante")])

        # Add special mods - augments and the like
        mods.extend(
            [
                mod
                for mod in self.mods
                if mod.compat not in regular_compats
                and mod.compat in weapon.name.upper()
                and weapon.name != "Vaykor Hek"
            ]
        )

        modlist = Modlist()
        modlist.mods = mods

        return modlist

    def __len__(self):
        return len(self.mods)

    def add(self, mod):
        self.mods.append(mod)

    def remove(self, mod):
        self.mods.remove(mod)

    def __add__(self, other):
        res = Modlist()
        res.mods.extend(self.mods)
        res.mods.extend(other.mods)
        return res

    # Returns the coefficient matrix of all mod stat values
    def matrix(self):
        return [self.mods[i].stats() for i in range(len(self))]

    def index(self, name):
        if self[name]:
            return self.mods.index(self[name])
        else:
            return []

    def element_indices(self):
        indices = [i for i in range(len(self)) if self.mods[i].element > 0]
        return indices

    def vigilante_indices(self):
        indices = [
            i for i in range(len(self)) if self.mods[i].name.startswith("Vigilante")
        ]
        return indices

    def conditional_indices(self):
        indices = [i for i in range(len(self)) if self.mods[i].conditional]
        return indices

    def names(self):
        return "\n".join(["[" + mod.name + "]" for mod in self.mods])


MODS_URL = "https://raw.githubusercontent.com/WFCD/warframe-items/development/data/json/Mods.json"
r = requests.get(url=MODS_URL)
mod_data = r.json()

names = Mod().stat_names()

elements = [
    "Electricity",
    "Toxin",
    "Heat",
    "Cold",
    "Corrosive",
    "Blast",
    "Radiation",
    "Viral",
    "Gas",
    "Magnetic",
]

stat_group = "(" + "|".join(names + elements)
stat_group = re.sub("_", " ", stat_group).title()
stat_regex = r"([\+-]\d+)% (<.*>)?" + stat_group + r")(.*)"

all_mods = Modlist()

for mod in mod_data:

    # TODO: Archgun mods

    if (
        "compatName" not in mod
        or mod["type"]
        not in [
            "Primary",
            "Rifle",
            "Secondary",
            "Secondary Mod",
            "Shotgun",
            "Shotgun Mod",
        ]
        or mod["uniqueName"].endswith("Beginner")  # Beginner mods
        or mod["name"].endswith("Riven Mod")  # Some kind of placeholder
        or "PvPMods" in mod["uniqueName"]  # Conclave mods
    ):
        continue

    conditional = False

    m = Mod(mod["name"])  # Create mod

    for line in mod["levelStats"][-1]["stats"]:  # Max rank stats

        match = re.search(stat_regex, line)

        if not match:  # Skip mods that aren't relevant for DPS
            continue

        if match.group(4):  # There is text after the stat increase

            if ":" in line:  # Covers "On kill:" and similar
                conditional = True

            if match.group(4) in [
                " to Grineer",
                " to Corpus",
                " to Infested",
                " to Corrupted",
                " on first shot in Magazine",
                " Radius",
            ]:  # Skip faction mods, charged/primed chamber, blast radius
                continue

        # Get the stat to increase
        stat = match.group(3)
        stat = re.sub(" ", "_", stat).lower()

        # All elements go into the same stat
        if stat.title() in elements:
            stat = "element"

        # Get the amount
        amount = float(match.group(1)) / 100

        # Add stat
        m.increase(stat, amount)

    if m:  # The mod has at least one non-zero stat

        m.conditional = conditional
        m.compat = mod["compatName"]

        if m.name == "Hell'S Chamber":  # Typo in the API
            m.name = "Hell's Chamber"

        all_mods.add(m)


# Remove non-unique amalgam mods and mods that have a primed version
for mod in all_mods.mods[:]:
    if (mod.name.startswith("Amalgam") and all_mods[mod.name[8:]]) or (
        all_mods["Primed " + mod.name]
    ):
        all_mods.remove(mod)

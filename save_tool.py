"""F1 Manager 24 save workflow: unpack a save for editing, then repack and install it.

  python save_tool.py unpack save14     extract save14's live database to work/save14_db1.db
  python save_tool.py install save14    back up the game's save14.sav, then install work/save14_db1.db into it
  python save_tool.py list              list saves in the game folder
  python save_tool.py setup [save17]    show your cars' perfect setup (newest save if no slot; save during a race weekend)

You can keep the .db open in VS Code the whole time: edit, install, edit more, install again.
work/ only holds <slot>_db1.db and a small <slot>.stamp that records which game save it came from.
The save header and the career-start snapshot (db2) are taken from the game's save at install time.
"""
import hashlib, os, sqlite3, struct, subprocess, sys, time, zlib


def layout(d):
    # compressed block = [u32 compLen][u32 db1][u32 db2][u32 db3] + zlib data running to EOF
    for i in range(16, len(d)):
        if d[i] == 0x78 and struct.unpack_from('<I', d, i - 16)[0] == len(d) - i:
            return (i,) + struct.unpack_from('<III', d, i - 12)
    raise ValueError("compressed block not found - not an F1 Manager 24 save?")


HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
BACKUPS = os.path.join(HERE, "backups")
KEEP_BACKUPS = 5  # per save slot
GAME_SAVES = os.environ.get("F1_SAVE_DIR") or os.path.join(os.environ["LOCALAPPDATA"], "F1Manager24", "Saved", "SaveGames")


def die(msg):
    print("ERROR:", msg)
    sys.exit(1)


def confirm(question):
    try:
        return input(question + " [y/N]: ").strip().lower() == "y"
    except EOFError:
        return False


def game_running():
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    return "f1manager24" in out


def slot_name(arg):
    s = arg.strip()
    if s.lower().endswith(".sav"):
        s = s[:-4]
    if s.isdigit():
        s = "save" + s
    return s


def paths(slot):
    return (os.path.join(GAME_SAVES, slot + ".sav"),
            os.path.join(WORK, slot + "_db1.db"),
            os.path.join(WORK, slot + ".stamp"))


def read_game_save(path):
    d = open(path, "rb").read()
    i, s1, s2, _ = layout(d)
    raw = zlib.decompress(d[i:])
    return d, i, raw[:s1], raw[s1:s1 + s2]


def db_bytes(path):
    # read through SQLite so an open editor tab can't hand us a half-written file
    c = sqlite3.connect(path)
    try:
        return c.serialize()
    finally:
        c.close()


def write_db(path, data):
    # SQLite's backup API writes into the file in place, so this works even while it's open in VS Code
    src = sqlite3.connect(":memory:")
    src.deserialize(data)
    dst = sqlite3.connect(path)
    try:
        src.backup(dst)
    except sqlite3.OperationalError as e:
        die(f"couldn't write {os.path.basename(path)} ({e}). It may be mid-edit in VS Code; save or close the tab and retry.")
    finally:
        dst.close()
        src.close()


def summary(path):
    c = sqlite3.connect(path)
    season = c.execute("select * from Player_State").fetchone()[1]
    team, bal = c.execute("select t.TeamName, b.Balance from Player p join Teams t on t.TeamID=p.TeamID "
                          "join Finance_TeamBalance b on b.TeamID=p.TeamID").fetchone()
    c.close()
    return f"season {season}, team {team}, balance ${bal:,}"


def unpack(slot):
    if game_running():
        die("F1 Manager 24 is running. Save and quit to the desktop first.")
    save, db, stamp = paths(slot)
    if not os.path.exists(save):
        die(f"{save} not found. Run 'List saves' to see what's there.")
    d, _, db1, _ = read_game_save(save)
    os.makedirs(WORK, exist_ok=True)

    if os.path.exists(db):
        if db_bytes(db) != db1 and not confirm(
                f"work/{slot}_db1.db has edits that aren't installed yet. Discard them and unpack fresh?"):
            die(f"kept your edits. Run 'Repack & install' for {slot} to install them.")
        write_db(db, db1)
    else:
        open(db, "wb").write(db1)
    open(stamp, "w").write(hashlib.sha256(d).hexdigest())
    print(f"Unpacked {slot}: {summary(db)}")
    print(f"Open work/{slot}_db1.db, edit, then run 'Repack & install' (Ctrl+Shift+B). The tab can stay open.")


def install(slot):
    if game_running():
        die("F1 Manager 24 is running. Quit to the desktop first, or the game will overwrite your edit.")
    save, db, stamp = paths(slot)
    if not (os.path.exists(db) and os.path.exists(stamp)):
        die(f"nothing to install for {slot}. Run 'Unpack save' for {slot} first.")
    if not os.path.exists(save):
        die(f"{save} not found in the game folder.")
    if os.path.exists(db + "-journal") or os.path.exists(db + "-wal"):
        die(f"work/{slot}_db1.db has an edit in progress. Save (Ctrl+S) in the editor first.")

    d, i, _, db2 = read_game_save(save)
    if hashlib.sha256(d).hexdigest() != open(stamp).read().strip():
        if not confirm(f"The game's {slot}.sav changed since you unpacked (you played or saved since). "
                       f"Installing will discard that progress. Continue?"):
            die(f"cancelled. Unpack {slot} again and redo the edit.")

    a = db_bytes(db)
    chk = sqlite3.connect(":memory:")
    chk.deserialize(a)
    ok = chk.execute("pragma integrity_check").fetchone()[0]
    chk.close()
    if ok != "ok":
        die(f"database integrity check failed: {ok}")

    os.makedirs(BACKUPS, exist_ok=True)
    bk = os.path.join(BACKUPS, f"{slot}_{time.strftime('%Y%m%d-%H%M%S')}.sav")
    open(bk, "wb").write(d)
    print("Backed up game save to", os.path.relpath(bk, HERE))

    comp = zlib.compress(a + db2, 9)
    out = d[:i - 16] + struct.pack("<IIII", len(comp), len(a), len(db2), 0) + comp
    j, s1, s2, _ = layout(out)
    assert zlib.decompress(out[j:]) == a + db2 and (s1, s2) == (len(a), len(db2))
    tmp = save + ".tmp"
    open(tmp, "wb").write(out)
    os.replace(tmp, save)
    print(f"Installed {slot}.sav ({summary(db)}). Load it in-game to check.")

    # done with the work files; if the tab is still open, keep them in sync so you can edit and install again
    try:
        os.remove(db)
        os.remove(stamp)
        print(f"Cleared work/{slot}.")
    except PermissionError:
        open(stamp, "w").write(hashlib.sha256(out).hexdigest())
        print(f"work/{slot}_db1.db is still open in VS Code, so it stays. Keep editing and install again any time, "
              f"or close the tab; it's cleared on the next install.")
    prune_backups(slot)


def prune_backups(slot, keep=KEEP_BACKUPS):
    mine = sorted(f for f in os.listdir(BACKUPS) if f.startswith(slot + "_") and f.endswith(".sav"))
    for f in mine[:-keep]:
        os.remove(os.path.join(BACKUPS, f))
    if len(mine) > keep:
        print(f"Removed {len(mine) - keep} old {slot} backup(s); keeping the newest {keep}.")


# in-game labels for each slider step (step = stored 0-1 value * number of steps)
SETUP_SLIDERS = [
    ("Front wing angle", "FrontWingAngle", [f"{x * 0.5:.1f}" for x in range(21)]),
    ("Rear wing angle", "RearWingAngle", [f"{9 + x * 0.5:.1f}" for x in range(15)]),
    ("Anti-roll distribution", "AntiRollBars", [f"{9 - x}:{1 + x}" for x in range(9)]),
    ("Tyre camber", "Camber", [f"{-2.7 - x * 0.05:.2f}" for x in range(17)]),
    ("Toe-out", "Toe", [f"{x * 0.05:.2f}" for x in range(21)]),
]


def newest_save():
    saves = [f for f in os.listdir(GAME_SAVES) if f.endswith(".sav") and f.startswith(("save", "autosave"))]
    return max(saves, key=lambda f: os.path.getmtime(os.path.join(GAME_SAVES, f)))[:-4]


def show_setup(slot):
    # reads straight from the game's save; nothing is unpacked or changed
    if slot in ("", "latest"):
        slot = newest_save()
    save = paths(slot)[0]
    if not os.path.exists(save):
        die(f"{save} not found.")
    _, _, db1, _ = read_game_save(save)
    c = sqlite3.connect(":memory:")
    c.deserialize(db1)
    c.row_factory = sqlite3.Row
    race = c.execute("select t.Name from Save_Weekend w join Races r on r.RaceID = w.RaceID "
                     "join Races_Tracks t on t.TrackID = r.TrackID").fetchone()
    cars = c.execute("select * from Save_CarConfig where TeamID = (select TeamID from Player) "
                     "order by LoadoutID").fetchall()
    if not race or not cars:
        die(f"{slot} isn't saved during a race weekend, so there's no setup data. "
            f"Save during a practice session and try again.")
    print(f"{slot}: perfect setup for {race['Name']}\n")
    for car in cars:
        # LoadoutID 0/1 = car number 1/2
        drv = c.execute("""select s.FirstName, s.LastName from Staff_Contracts k
                           join Staff_DriverData d on d.StaffID = k.StaffID
                           join Staff_BasicData s on s.StaffID = k.StaffID
                           where k.TeamID = ? and k.ContractType = 0 and d.AssignedCarNumber = ?""",
                        (car["TeamID"], car["LoadoutID"] + 1)).fetchone()
        name = " ".join(clean_name(n) for n in drv) if drv else "?"
        print(f"Car {car['LoadoutID'] + 1} - {name}")
        for label, col, steps in SETUP_SLIDERS:
            step = round(car["PerfectSetup" + col] * (len(steps) - 1))
            cur = round(car["CurrentSetup" + col] * (len(steps) - 1))
            note = "" if cur == step else f"   (now {steps[cur]})"
            print(f"  {label:24s} {steps[step]:>8s}{note}")
        print()
    c.close()


def clean_name(n):
    if n.startswith("[STRING_LITERAL"):
        return n.split("|")[1]
    return n.rstrip("]").split("_")[-1]


def list_saves():
    for f in sorted(os.listdir(GAME_SAVES)):
        if f.endswith(".sav") and f.startswith("save"):
            p = os.path.join(GAME_SAVES, f)
            pending = " (unpacked in work/)" if os.path.exists(paths(f[:-4])[1]) else ""
            print(f"{f:22s} {time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(p)))}{pending}")


def ask():
    # run with no arguments (e.g. the VS Code Run button): ask instead of failing
    print("F1 Save Tools\n  1) Unpack a save\n  2) Repack & install a save\n  3) List saves\n  4) Show perfect setup")
    choice = input("Choose 1-4: ").strip()
    cmd = {"1": "unpack", "2": "install", "3": "list", "4": "setup"}.get(choice) or die("expected 1-4")
    if cmd == "list":
        return [cmd]
    if cmd == "setup":
        return [cmd, input("Save slot (Enter for the newest save): ").strip() or "latest"]
    slot = input("Save slot (e.g. 14 or save14): ").strip() or die("no save slot entered")
    return [cmd, slot]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.argv[1:] = ask()
    elif sys.argv[1] in ("unpack", "install") and (len(sys.argv) < 3 or not sys.argv[2].strip()):
        die("no save slot entered. Type a slot like 14 or save14 when the task asks.")
    cmd = sys.argv[1]
    if cmd == "list":
        list_saves()
    elif cmd == "setup":
        arg = sys.argv[2].strip() if len(sys.argv) > 2 else "latest"
        show_setup("latest" if arg in ("", "latest") else slot_name(arg))
    elif cmd in ("unpack", "install"):
        (unpack if cmd == "unpack" else install)(slot_name(sys.argv[2]))
    else:
        die(__doc__)

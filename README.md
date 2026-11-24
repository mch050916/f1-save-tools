# F1 Save Tools

Edit F1 Manager 24 saves in VS Code.

## Workflow

1. **Save and quit the game to the desktop.**
2. `Ctrl+Shift+P` → **Tasks: Run Task** → **Unpack save** → type the slot (e.g. `save14` or `14`).
3. Open `work/save14_db1.db`. It opens in the SQLite3 Editor grid. Pick a table, double-click a cell to edit, or run queries from `queries.sql`.
4. `Ctrl+S` to commit your edits to the .db file.
5. `Ctrl+Shift+B` (**Repack & install**) → same slot. It backs up the game's current save to `backups/` first (newest 5 per slot are kept). The tab can stay open: edit more and install again whenever you like. Once the tab is closed, the next install clears `work/`.
6. Launch the game and load the save. If Steam shows a cloud conflict, choose the **local** files.

## Notes

- `work/` holds only `<slot>_db1.db` (the live career you edit) and `<slot>.stamp` (which game save it came from).
- If you've played since unpacking, install asks before overwriting that progress. Unpacking over edits you haven't installed also asks first.
- To undo: copy a file from `backups/` back to `%LOCALAPPDATA%\F1Manager24\Saved\SaveGames` and rename it to e.g. `save14.sav`.
- Safe to edit: money, staff/driver stats, contracts, rules values. Risky: car part performance (the 2026 mod's Lite database warns about this). Don't change IDs.

## Useful tables

| What | Table | Key columns |
|---|---|---|
| Money | `Finance_TeamBalance` | TeamID, Balance |
| Your team | `Player` | TeamID (you are Williams = 6) |
| Teams | `Teams` | TeamID, TeamName |
| People | `Staff_BasicData` | StaffID, FirstName, LastName |
| Stats | `Staff_PerformanceStats` | StaffID, StatID, Val, Max (StatID names in `Staff_Enum_PerformanceStatTypes`) |
| Driver traits | `Staff_DriverData` | Improvability, Aggression, Marketability |
| Contracts | `Staff_Contracts` | TeamID, PosInTeam, Salary, EndSeason |
| Staff role | `Staff_GameData` | StaffType: 0 Driver, 1 Tech Chief, 2 Race Eng, 3 Head of Aero, 4 Sporting Dir |
| Car parts | `Parts_Designs`, `Parts_Designs_StatValues` | stat names in `Parts_Enum_Stats` |
| Rules | `Regulations_Enum_Changes` | Name, CurrentValue |
| Facilities | `Buildings_HQ` | TeamID, BuildingType, DegradationValue |

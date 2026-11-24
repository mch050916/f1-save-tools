-- Handy queries for work/<slot>_db1.db.
-- In the SQLite3 Editor tab, paste one into the query box at the top and run it (Ctrl+Enter).
-- Changes take effect in the game only after "Repack & install" (Ctrl+Shift+B).

-- ===== Your team =====
SELECT p.FirstName, p.LastName, t.TeamID, t.TeamName, b.Balance
FROM Player p JOIN Teams t ON t.TeamID = p.TeamID JOIN Finance_TeamBalance b ON b.TeamID = p.TeamID;

-- Set your balance (dollars)
UPDATE Finance_TeamBalance SET Balance = 50000000 WHERE TeamID = (SELECT TeamID FROM Player);

-- ===== All teams' money =====
SELECT t.TeamID, t.TeamName, b.Balance FROM Finance_TeamBalance b JOIN Teams t USING (TeamID) ORDER BY t.TeamID;

-- ===== Drivers with readable names, team, and contract =====
-- Names are stored as keys like [StaffName_Forename_Male_Lewis] or [STRING_LITERAL:Value=|Jon|]; this strips them.
SELECT s.StaffID,
       CASE WHEN s.FirstName LIKE '[STRING_LITERAL%' THEN substr(s.FirstName, instr(s.FirstName, '|') + 1, length(s.FirstName) - instr(s.FirstName, '|') - 2) ELSE replace(replace(replace(replace(s.FirstName, '[StaffName_Forename_Male_', ''), '[StaffName_Forename_Female_', ''), '[StaffName_Surname_', ''), ']', '') END AS First,
       CASE WHEN s.LastName LIKE '[STRING_LITERAL%' THEN substr(s.LastName, instr(s.LastName, '|') + 1, length(s.LastName) - instr(s.LastName, '|') - 2) ELSE replace(replace(replace(replace(s.LastName, '[StaffName_Forename_Male_', ''), '[StaffName_Forename_Female_', ''), '[StaffName_Surname_', ''), ']', '') END AS Last,
       t.TeamName, c.PosInTeam, c.Salary, c.EndSeason, d.Improvability, d.Aggression, d.Marketability
FROM Staff_BasicData s
JOIN Staff_GameData g ON g.StaffID = s.StaffID AND g.StaffType = 0
LEFT JOIN Staff_Contracts c ON c.StaffID = s.StaffID AND c.ContractType = 0
LEFT JOIN Teams t ON t.TeamID = c.TeamID
LEFT JOIN Staff_DriverData d ON d.StaffID = s.StaffID
WHERE c.TeamID <= 10 OR c.TeamID = 32
ORDER BY c.TeamID, c.PosInTeam;

-- ===== One person's stats (change 3 to the StaffID from the query above) =====
SELECT ps.StaffID, ps.StatID, e.Name AS Stat, ps.Val, ps.Max
FROM Staff_PerformanceStats ps JOIN Staff_Enum_PerformanceStatTypes e ON e.Value = ps.StatID
WHERE ps.StaffID = 3;

-- Boost every stat for one person (capped at 100)
UPDATE Staff_PerformanceStats SET Val = min(Val + 5, 100) WHERE StaffID = 3;

-- ===== Your staff (non-drivers) =====
-- StaffType: 1 Technical Chief, 2 Race Engineer, 3 Head of Aero, 4 Sporting Director
SELECT s.StaffID, g.StaffType, CASE WHEN s.FirstName LIKE '[STRING_LITERAL%' THEN substr(s.FirstName, instr(s.FirstName, '|') + 1, length(s.FirstName) - instr(s.FirstName, '|') - 2) ELSE replace(replace(replace(replace(s.FirstName, '[StaffName_Forename_Male_', ''), '[StaffName_Forename_Female_', ''), '[StaffName_Surname_', ''), ']', '') END AS First, CASE WHEN s.LastName LIKE '[STRING_LITERAL%' THEN substr(s.LastName, instr(s.LastName, '|') + 1, length(s.LastName) - instr(s.LastName, '|') - 2) ELSE replace(replace(replace(replace(s.LastName, '[StaffName_Forename_Male_', ''), '[StaffName_Forename_Female_', ''), '[StaffName_Surname_', ''), ']', '') END AS Last, c.Salary, c.EndSeason
FROM Staff_Contracts c JOIN Staff_BasicData s USING (StaffID) JOIN Staff_GameData g USING (StaffID)
WHERE c.TeamID = (SELECT TeamID FROM Player) AND g.StaffType > 0 AND c.ContractType = 0;

-- ===== Current rules (cost cap, part limits, etc.) =====
SELECT ChangeID, Name, CurrentValue, MinValue, MaxValue FROM Regulations_Enum_Changes;

-- ===== Swap car 1 and car 2 (each driver keeps their race engineer) =====
-- Car 1 driver + engineer become car 2, and car 2 driver + engineer become car 1.
-- Run both statements together. Running them again swaps back.
UPDATE Staff_Contracts SET PosInTeam = 3 - PosInTeam
WHERE TeamID = (SELECT TeamID FROM Player) AND ContractType = 0 AND PosInTeam IN (1, 2)
  AND StaffID IN (SELECT StaffID FROM Staff_GameData WHERE StaffType IN (0, 2));
UPDATE Staff_DriverData SET AssignedCarNumber = 3 - AssignedCarNumber
WHERE AssignedCarNumber IN (1, 2)
  AND StaffID IN (SELECT StaffID FROM Staff_Contracts WHERE TeamID = (SELECT TeamID FROM Player) AND ContractType = 0);

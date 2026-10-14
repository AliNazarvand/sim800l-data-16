# Cross-Reference Report

Generated: 2026-10-13T23:39:39Z

AT command index: **365** unique commands

| Rule | OK | Mismatch | Invalid |
|---|---|---|---|
| dat_02 related_command -> dat_01 | 97 | 0 | 0 |
| dat_04 related_command -> dat_01 | 0 | 0 | 0 |
| dat_05 related_commands -> dat_01 | 35 | 5 | 1 |
| dat_06 command -> dat_01 | 25 | 1 | 2 |
| dat_09 command -> dat_01 | 14 | 0 | 0 |
| dat_10 command -> dat_01 | 21 | 3 | 0 |
| dat_11 command -> dat_01 | 20 | 18 | 0 |
| dat_12 command -> dat_01 | 9 | 4 | 0 |
| dat_13 command -> dat_01 | 10 | 0 | 0 |
| dat_15 command -> dat_01 | 0 | 0 | 0 |
| dat_17 command -> dat_01 | 0 | 9 | 0 |

**Totals** — OK: 231, mismatch: 40, invalid: 3

Interpretation:
- **OK**: reference resolves to an entry present in dat_01.
- **Mismatch**: reference normalizes to a well-formed AT command that is not yet in dat_01. This usually means dat_01 is missing that command, not that the reference is wrong. Tracked as `pending` for future dat_01 completion.
- **Invalid**: reference does not normalize to a valid AT-command token (typically empty or a state name).
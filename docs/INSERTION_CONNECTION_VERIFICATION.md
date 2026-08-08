# Y2L Insertion Connection Type — binary verification

Date: 2026-08-08

Three otherwise-identical `Init Normal` Y2L files were exported from MODX M / ESP with only **Insertion Connection** changed. All files were 38,985 bytes. The routing-dependent byte was isolated at file offset 7620. In the DPFM Performance blob this is Part Common relative offset **+232** (Part 1 blob absolute offset **6933**).

| UI setting | Stored u8 |
|---|---:|
| Parallel | 0 |
| Ins A → B | 1 |
| Ins B → A | 2 |

This agrees with Yamaha's MODX M / MONTAGE M Data List semantic ordering. The field is independent of per-element `elem_connect`, which chooses the insertion block an element enters.

The corresponding classic X7L/X8L source field/index has not yet been binary-identified. Code converting classic data to Y2L must preserve the template/default routing rather than guess a source mapping.

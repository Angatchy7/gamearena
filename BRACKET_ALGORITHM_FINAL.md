# GameArena Final Compact Knockout Bracket

## Rules
- Shuffle registered participants before bracket generation.
- If the current participant/match count is even, pair all participants with no bye.
- If the current count is odd, create exactly one bye slot and assign it randomly.
- Create only the number of matches required for that round; never pad the bracket to 8/16/32/64 solely to satisfy a power-of-two structure.
- A bye is an automatic advancement, not a fake participant/team record.
- Later rounds are built from the number of advancing match winners using the same compact rule.
- Match-to-match connectors use each `Match.next_match` relationship so the visual bracket follows the actual generated tree, including randomly positioned byes.

## Example
For 9 participants, Round 1 contains 5 fixtures: four real matches and one bye. Later rounds contain only the necessary matches (3, then 2, then the final).

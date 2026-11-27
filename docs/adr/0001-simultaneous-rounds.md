# Simultaneous Rounds instead of turns

TrackBack started with a sequential mode, where Players took turns placing Songs, and later added a simultaneous mode. We kept only simultaneous Rounds: every connected Player places the same Song at the same time, and the next Song plays once all of them have guessed. Nobody waits for the others to take their turns, and the whole party is involved in every Song. The unused sequential mode was removed in 4d29be2.

## Consequences

- The `your_turn` wire message is left over from the turn-based design. It means "place the current Song", not that a Player has a turn. It keeps its name for client compatibility, while the code calls it a guess request. See **Round** and **Guess** in `GLOSSARY.md`, and the wire-name table in `docs/websocket-protocol.md`.
- A Round never waits for Disconnected Players, so a Player who Rejoins has missed the Songs played while they were away.
- Two Players can reach the Target Song Count in the same Round. The first correct Guess wins, so there are no ties.

# TrackBack

A music party game: Players hear Songs from a playlist and place each one into their own Timeline by Release Year. The first to grow their Timeline to the Target Song Count wins.

## Language

### People

**Player**:
A person taking part in a Game Session, identified by their Username.
_Avoid_: User, Member

**Host**:
The Player who creates a Game Session and starts it.
_Avoid_: Admin, Owner

**Server Operator**:
The person who installs, configures and runs the TrackBack server.
_Avoid_: Host

**Disconnected Player**:
A Player whose connection dropped after the Game Session started; they keep their Timeline and can Rejoin.
_Avoid_: Inactive player, Left player

**Rejoin**:
A Disconnected Player reconnecting to their running Game Session under the same Username.
_Avoid_: Return, Reconnect

### Game Session

**Game Session**:
One hosted game, from its Lobby until a Player wins, identified by its Game Session Name.
_Avoid_: Game, Session, Match

**Lobby**:
A Game Session before the Host starts it, while Players are still joining.
_Avoid_: Waiting room

**Target Song Count**:
The number of Songs a Player's Timeline must hold to win, chosen by the Host.
_Avoid_: Winning score, Goal

**Music Service**:
The external service that plays a Game Session's Songs, chosen by the Host.
_Avoid_: Provider, Adapter, Backend

**Mock Music Service**:
A Music Service with a fixed set of Songs and no real playback, for development only.
_Avoid_: Fake, Dummy service

### Play

**Song**:
A piece of music with a title, artist and Release Year, as played in a Round.
_Avoid_: Track, Card

**Release Year**:
The year a Song counts as released, which decides where it belongs in a Timeline.
_Avoid_: Date, Year of publication

**Timeline**:
A Player's Songs, ordered by Release Year, built from their correct Guesses.
_Avoid_: Song list, Deck

**Round**:
One Song that every connected Player places into their own Timeline at the same time.
_Avoid_: Turn

**Guess**:
A Player's placement of the current Song at a position in their Timeline. It is correct when the Timeline stays ordered by Release Year; Songs with equal Release Years may sit in any order. A wrong Guess only means the Song is not added.
_Avoid_: Turn, Move, Choice

**Winner**:
The Player whose correct Guess first brings their Timeline to the Target Song Count. There are no ties.
